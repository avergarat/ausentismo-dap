"""
Análisis granular por CESFAM / Establecimiento
"""
import streamlit as st
from modules.sidebar_css import inject as _inject_css
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from modules.db import get_catalogo, get_periodo, init_db
from modules.metrics import build_df, kpis_por_cesfam, ia_serie_mensual, dist_tipo_lm, META_IA
from modules.ui import show_table

init_db()
_inject_css()

st.title("🏥 Análisis por Establecimiento")
st.divider()

# ── Sidebar ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔍 Filtros")
    unidades  = get_catalogo('licencias', 'nombre_unidad')
    plantas   = get_catalogo('licencias', 'planta')
    periodo   = get_periodo()

    sel_u   = st.multiselect("Establecimientos", unidades, placeholder="Todos")
    sel_p   = st.multiselect("Planta", plantas, placeholder="Todas")
    fi      = st.text_input("Desde", value=periodo[0] or '')
    ff      = st.text_input("Hasta", value=periodo[1] or '')
    dot     = st.number_input("Dotación promedio", value=1602, step=10)

@st.cache_data(ttl=120, show_spinner="Calculando...")
def cargar(u, p, fi, ff, d):
    df = build_df(unidades=u or None, plantas=p or None,
                  fecha_ini=fi or None, fecha_fin=ff or None)
    return df

df = cargar(tuple(sel_u), tuple(sel_p), fi, ff, dot)
if df.empty:
    st.warning("Sin datos. Carga los archivos en 📥 Cargar Datos.")
    st.stop()

cesfam_df = kpis_por_cesfam(df, dot)

# ── Tabla comparativa ─────────────────────────────────────────────────────
st.subheader("📊 Tabla Comparativa — Todos los Establecimientos")

if not cesfam_df.empty:
    def _sem_badge(s):
        icons = {'VERDE':'🟢','AMARILLO':'🟡','ROJO':'🔴'}
        return f"{icons.get(s,'⚪')} {s}"

    disp = cesfam_df.copy()
    disp['Semáforo'] = disp['semaforo'].apply(_sem_badge)
    disp['Costo'] = disp['costo_total'].apply(lambda x: f"${x:,.0f}")
    disp = disp.rename(columns={
        'cesfam':'Establecimiento', 'n_lm':'N° LM', 'dias_total':'Días',
        'n_funcionarios':'Func.', 'ia_acumulado':'ÍA Acum.',
        'ia_mensual':'ÍA Mes', 'tasa_frecuencia':'TF', 'tasa_gravedad':'TG',
        'pct_corto':'% Corta', 'pct_prolongado':'% Prolong.',
        'n_recurrentes_5':'Recur ≥5', 'pct_muy_corto':'% ≤3d'
    })
    cols_show = ['Establecimiento','N° LM','Días','Func.','ÍA Acum.','ÍA Mes',
                 'TF','TG','% Corta','% ≤3d','% Prolong.','Recur ≥5','Costo','Semáforo']
    cols_show = [c for c in cols_show if c in disp.columns]
    show_table(disp[cols_show])

st.divider()

# ── Gráfico de barras ÍA por CESFAM ───────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 Índice de Ausentismo acumulado por CESFAM")
    if not cesfam_df.empty:
        fig = px.bar(
            cesfam_df.sort_values('ia_acumulado'),
            x='ia_acumulado', y='cesfam', orientation='h',
            color='semaforo',
            color_discrete_map={'VERDE':'#1E8B4C','AMARILLO':'#FFC000','ROJO':'#C00000'},
            text='ia_acumulado'
        )
        fig.add_vline(x=META_IA['MENSUAL'], line_dash='dash', line_color='orange',
                       annotation_text='Meta mensual')
        fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
        fig.update_layout(height=420, showlegend=True,
                          margin=dict(l=10,r=40,t=20,b=20),
                          xaxis_title='ÍA Acumulado', yaxis_title='')
        st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("💰 Costo Total LM por CESFAM")
    if not cesfam_df.empty:
        fig = px.bar(
            cesfam_df.sort_values('costo_total'),
            x='costo_total', y='cesfam', orientation='h',
            color_discrete_sequence=['#006FB9'],
            text='costo_total'
        )
        fig.update_traces(texttemplate='$%{text:,.0f}', textposition='outside',
                          textfont_size=8)
        fig.update_layout(height=420, showlegend=False,
                          margin=dict(l=10,r=80,t=20,b=20),
                          xaxis_title='Costo ($)', yaxis_title='')
        st.plotly_chart(fig, use_container_width=True)

# ── Drill-down por CESFAM ─────────────────────────────────────────────────
st.divider()
st.subheader("🔍 Detalle por Establecimiento")

cesfam_sel = st.selectbox("Selecciona un establecimiento", unidades)
if cesfam_sel:
    df_c = df[df['nombre_unidad'].str.strip().str.upper() == cesfam_sel.strip().upper()]

    if df_c.empty:
        st.info("Sin datos para este establecimiento.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("N° LM", f"{len(df_c):,}")
        c2.metric("Días ausentismo", f"{df_c['dias_periodo'].sum():,}")
        c3.metric("Funcionarios distintos", f"{df_c['rut'].nunique()}")
        c4.metric("Costo total", f"${df_c['costo'].sum():,.0f}")

        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("**Tendencia mensual ÍA**")
            serie_c = ia_serie_mensual(df_c, dot / 11)
            if not serie_c.empty:
                fig = px.line(serie_c, x='mes_key', y='ia_mensual',
                              markers=True, color_discrete_sequence=['#006FB9'])
                fig.add_hline(y=META_IA['MENSUAL'], line_dash='dash', line_color='orange')
                fig.update_layout(height=250, margin=dict(l=10,r=10,t=10,b=50),
                                  xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)

        with col_b:
            st.markdown("**Tipos de LM en este CESFAM**")
            dt_c = dist_tipo_lm(df_c)
            if not dt_c.empty:
                fig = px.pie(dt_c, values='n_lm', names='tipo_lm',
                             color='tipo_lm',
                             color_discrete_map={r['tipo_lm']: r['color']
                                                  for _, r in dt_c.iterrows()})
                fig.update_traces(textinfo='percent', textfont_size=9)
                fig.update_layout(height=250, showlegend=True,
                                  legend=dict(font_size=8),
                                  margin=dict(l=10,r=10,t=10,b=10))
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Distribución por planta en este CESFAM**")
        planta_c = (df_c.groupby('planta')
                       .agg(n_lm=('rut','count'), dias=('dias_periodo','sum'))
                       .reset_index()
                       .sort_values('dias', ascending=False))
        planta_c['pct'] = (planta_c['dias'] / planta_c['dias'].sum() * 100).round(1)
        planta_c = planta_c.rename(columns={'planta':'Planta','n_lm':'N° LM',
                                             'dias':'Días','pct':'% Días'})
        planta_c['Días'] = planta_c['Días'].apply(lambda x: f"{int(x):,}")
        show_table(planta_c)

        st.markdown("**Top 20 funcionarios con más días de LM en este CESFAM**")
        top_func = (df_c.groupby(['rut','nombre'])
                       .agg(n_lm=('rut','count'), dias=('dias_periodo','sum'),
                            costo=('costo','sum'))
                       .reset_index()
                       .sort_values('dias', ascending=False)
                       .head(20))
        top_func = top_func.rename(columns={'rut':'RUT','nombre':'Nombre',
                                             'n_lm':'N° LM','dias':'Días','costo':'Costo'})
        top_func['Costo'] = top_func['Costo'].apply(lambda x: f"${float(x):,.0f}")
        top_func['Días'] = top_func['Días'].apply(lambda x: f"{int(x):,}")
        show_table(top_func)
