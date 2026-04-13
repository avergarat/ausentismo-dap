"""
Dashboard principal — KPIs globales, semáforo, tendencia mensual
"""
import streamlit as st
from modules.sidebar_css import inject as _inject_css
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from modules.db import get_catalogo, get_periodo, init_db
from modules.ui import show_table
from modules.metrics import (
    build_df, kpis_globales, ia_serie_mensual, dist_tipo_lm,
    dist_duracion, dist_dia_semana, kpis_por_cesfam,
    comparativo_cortes, comparativo_anual_mensual,
    META_IA, SEMAFORO_COLORES, emoji_semaforo, fmt_peso, fmt_num
)

init_db()
_inject_css()

st.markdown("""
<style>
  h1,h2,h3 { color: #00386B; }
  .kpi-big { font-size: 2.2rem; font-weight: 700; color: #00386B; }
  .kpi-lbl { font-size: .8rem; color: #666; }
  .sem-verde   { color: #1E8B4C; font-weight: bold; }
  .sem-amarillo{ color: #FFC000; font-weight: bold; }
  .sem-rojo    { color: #C00000; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar filtros ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔍 Filtros Globales")
    unidades   = get_catalogo('licencias', 'nombre_unidad')
    plantas    = get_catalogo('licencias', 'planta')
    generos    = get_catalogo('licencias', 'genero')
    calidades  = get_catalogo('licencias', 'calidad_juridica')
    tipos_lm   = get_catalogo('licencias', 'tipo_lm')
    periodo    = get_periodo()

    sel_unidades = st.multiselect("Establecimiento", unidades, placeholder="Todos")
    sel_plantas  = st.multiselect("Planta / Estamento", plantas, placeholder="Todos")
    sel_generos  = st.multiselect("Género", generos, placeholder="Todos")
    sel_tipos    = st.multiselect("Tipo de LM", tipos_lm, placeholder="Todos")
    sel_calidad  = st.multiselect("Calidad Jurídica", calidades, placeholder="Todos")

    col_fi, col_ff = st.columns(2)
    with col_fi: fecha_ini = st.text_input("Desde (YYYY-MM-DD)", value=periodo[0] or '')
    with col_ff: fecha_fin = st.text_input("Hasta (YYYY-MM-DD)", value=periodo[1] or '')

    dot_prom = st.number_input("Dotación promedio", value=1602, step=10,
                                help="Denominador para calcular el ÍA")

    st.divider()
    anio_comp = st.selectbox("Año para comparativo cortes",
                              options=[2024, 2025, 2026], index=2)

# ── Cargar datos ──────────────────────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner="Calculando métricas...")
def cargar(unidades, plantas, generos, tipos, calidades, fi, ff, dot):
    filtros = dict(
        unidades=unidades or None, plantas=plantas or None,
        generos=generos or None, tipos_lm=tipos or None,
        calidades=calidades or None,
        fecha_ini=fi or None, fecha_fin=ff or None,
        excluir_cgr=True
    )
    df = build_df(**filtros)
    return df, kpis_globales(df, dot)

df, g = cargar(
    tuple(sel_unidades), tuple(sel_plantas), tuple(sel_generos),
    tuple(sel_tipos), tuple(sel_calidad), fecha_ini, fecha_fin, dot_prom
)

# ── Header ────────────────────────────────────────────────────────────────
st.title("📊 Dashboard de Ausentismo")
st.caption(f"Base de datos: **{len(df):,}** registros — dotación referencia: **{dot_prom:,}**")

if df.empty:
    st.warning("Sin datos para los filtros seleccionados.")
    st.stop()

# ── KPI Cards ─────────────────────────────────────────────────────────────
ia_m = g.get('ia_mensual', 0)
sem  = 'VERDE' if ia_m <= 2.17 else ('AMARILLO' if ia_m <= 2.60 else 'ROJO')

col1,col2,col3,col4,col5,col6,col7,col8 = st.columns(8)
kpis_display = [
    (col1, "LM totales",        f"{g['n_lm']:,}",            None),
    (col2, "Días ausentismo",   f"{g['dias_total']:,}",       None),
    (col3, "ÍA acumulado",      f"{g['ia_acumulado']:.2f}",   None),
    (col4, "ÍA mensual",        f"{g['ia_mensual']:.3f}",     f"Meta ≤ {META_IA['MENSUAL']}"),
    (col5, "Tasa Gravedad",     f"{g['tasa_gravedad']:.2f}d", None),
    (col6, "Tasa Frecuencia",   f"{g['tasa_frecuencia']:.2f}%",None),
    (col7, "Funcionarios",      f"{g['n_func']:,}",           None),
    (col8, "Costo total",       fmt_peso(g['costo_total']), None),
]
for col, lbl, val, delta in kpis_display:
    with col:
        st.metric(lbl, val, delta=delta)

# Semáforo global
sem_icon = {'VERDE':'🟢','AMARILLO':'🟡','ROJO':'🔴'}.get(sem,'⚪')
color_sem = {'VERDE':'success','AMARILLO':'warning','ROJO':'error'}.get(sem,'info')
meta_m = META_IA['MENSUAL']
getattr(st, color_sem)(
    f"{sem_icon} **Semáforo global:** {sem} — ÍA mensual {ia_m:.3f} "
    f"({'dentro' if ia_m <= meta_m else 'SOBRE'} de meta {meta_m})"
)

st.divider()

# ── Fila 1: Tendencia IA + Comparativo Cortes ──────────────────────────────
col_izq, col_der = st.columns([2, 1])

with col_izq:
    st.subheader("📈 Evolución del ÍA Mensual")
    serie = ia_serie_mensual(df, dot_prom)
    if not serie.empty:
        fig = go.Figure()
        colors_line = [SEMAFORO_COLORES.get(s, '#006FB9') for s in serie['semaforo']]
        fig.add_trace(go.Scatter(
            x=serie['mes_key'], y=serie['ia_mensual'],
            mode='lines+markers', name='ÍA Mensual',
            line=dict(color='#006FB9', width=2.5),
            marker=dict(color=colors_line, size=9, line=dict(color='white',width=1))
        ))
        fig.add_trace(go.Scatter(
            x=serie['mes_key'], y=serie['ia_acumulado'],
            mode='lines', name='ÍA Acumulado',
            line=dict(color='#00386B', width=1.5, dash='dot')
        ))
        fig.add_hline(y=META_IA['MENSUAL'], line_dash='dash', line_color='#FFC000',
                       annotation_text=f"Meta mensual {META_IA['MENSUAL']}", annotation_position='top right')
        fig.add_hline(y=2.60, line_dash='dot', line_color='#C00000',
                       annotation_text="Nivel crítico 2.60", annotation_position='bottom right')
        fig.update_layout(
            height=320, margin=dict(l=10,r=10,t=30,b=60),
            legend=dict(orientation='h', y=-0.25),
            xaxis=dict(tickangle=-45), yaxis_title='ÍA (días/func)',
            plot_bgcolor='white', paper_bgcolor='white'
        )
        st.plotly_chart(fig, use_container_width=True)

with col_der:
    st.subheader("🏆 Comparativo por Corte")
    df_cortes = comparativo_cortes(df, anio_comp, dot_prom)
    if not df_cortes.empty:
        for _, r in df_cortes.iterrows():
            delta_val = r['delta']
            delta_str = f"{delta_val:+.2f} vs meta"
            st.metric(
                label=f"{r['cumple']} {r['corte']} {anio_comp}",
                value=f"ÍA {r['ia_acumulado']:.2f}",
                delta=delta_str,
                delta_color='inverse'
            )

st.divider()

# ── Fila 2: Tipo LM + Duración ─────────────────────────────────────────────
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("🥧 Tipos de LM")
    dt = dist_tipo_lm(df)
    if not dt.empty:
        fig = px.pie(dt, values='n_lm', names='tipo_lm',
                     color='tipo_lm', color_discrete_map={
                         row['tipo_lm']: row['color'] for _, row in dt.iterrows()
                     },
                     hover_data=['dias','pct_dias'])
        fig.update_traces(textposition='inside', textinfo='percent+label',
                          textfont_size=9)
        fig.update_layout(height=340, showlegend=False,
                          margin=dict(l=10,r=10,t=20,b=10))
        st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.subheader("📏 Distribución por Duración")
    dd = dist_duracion(df)
    if not dd.empty:
        fig = px.bar(dd, x='rango_duracion', y='n_lm',
                     text='pct', color='n_lm',
                     color_continuous_scale=['#D6E8F7','#006FB9','#00386B'])
        fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig.update_layout(height=340, showlegend=False,
                          coloraxis_showscale=False,
                          margin=dict(l=10,r=10,t=20,b=40),
                          xaxis_title='Duración', yaxis_title='N° LM')
        st.plotly_chart(fig, use_container_width=True)

# ── Fila 3: Día de inicio + Género ────────────────────────────────────────
col_c, col_d = st.columns(2)

with col_c:
    st.subheader("📅 Inicio LM por Día de la Semana")
    dds = dist_dia_semana(df)
    if not dds.empty:
        fig = px.bar(dds, x='dia_es', y='n_lm', text='pct',
                     color_discrete_sequence=['#006FB9'])
        fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig.update_layout(height=300, margin=dict(l=10,r=10,t=20,b=40),
                          showlegend=False, xaxis_title='', yaxis_title='N° LM')
        st.plotly_chart(fig, use_container_width=True)

with col_d:
    st.subheader("⚡ ÍA mensual por establecimiento (mapa de calor)")
    if not df.empty and 'nombre_unidad' in df.columns:
        pivot = (df.groupby(['mes_key','nombre_unidad'])['dias_periodo']
                   .sum()
                   .unstack(fill_value=0))
        pivot_ia = pivot / dot_prom * 11  # normalizar por CESFAM ~1/11 dotación
        if not pivot_ia.empty:
            fig = px.imshow(pivot_ia.T,
                            color_continuous_scale=['#D6E8F7','#FFC000','#C00000'],
                            aspect='auto', labels=dict(x='Mes', y='CESFAM', color='ÍA'))
            fig.update_layout(height=300, margin=dict(l=10,r=10,t=20,b=40))
            st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Tabla semáforo CESFAM ─────────────────────────────────────────────────
st.subheader("🚦 Semáforo por Establecimiento")
cesfam_df = kpis_por_cesfam(df, dot_prom)
if not cesfam_df.empty:
    display = cesfam_df[[
        'cesfam','n_lm','dias_total','n_funcionarios',
        'ia_acumulado','ia_mensual','tasa_frecuencia','tasa_gravedad',
        'pct_corto','pct_prolongado','n_recurrentes_5','costo_total','semaforo'
    ]].copy()
    display.columns = [
        'Establecimiento','N° LM','Días','Func.',
        'ÍA Acum.','ÍA Mes','TF','TG',
        '% Corta','% Prolong.','Recur ≥5','Costo','Semáforo'
    ]
    display['Costo'] = display['Costo'].apply(lambda x: fmt_peso(x))
    display['Semáforo'] = display['Semáforo'].apply(
        lambda s: f"{'🟢' if s=='VERDE' else '🟡' if s=='AMARILLO' else '🔴'} {s}"
    )
    show_table(display)

st.divider()

# ── Comparativo anual mensual ─────────────────────────────────────────────
st.subheader("📅 Índice de Ausentismo Comparativo Anual")
comp = comparativo_anual_mensual(df, dot_prom)
if not comp.empty and comp['anio'].nunique() > 1:
    MESES_ORDEN = ['ENE','FEB','MAR','ABR','MAY','JUN',
                   'JUL','AGO','SEP','OCT','NOV','DIC']
    años = sorted(comp['anio'].unique())
    COLORES_A = ['#C00000','#FFC000','#1E8B4C','#006FB9','#5B9BD5']
    fig_comp = go.Figure()
    for i, anio in enumerate(años):
        sub = comp[comp['anio'] == anio].sort_values('mes')
        fig_comp.add_trace(go.Scatter(
            x=sub['mes_nom'], y=sub['ia'],
            mode='lines+markers', name=str(anio),
            line=dict(color=COLORES_A[i % len(COLORES_A)], width=2.5),
            marker=dict(size=7),
            text=[f"{v:.2f}" for v in sub['ia']],
            textposition='top center',
            hovertemplate=f"<b>{anio} %{{x}}</b><br>ÍA: %{{y:.3f}}<extra></extra>"
        ))
    fig_comp.add_hline(y=META_IA['MENSUAL'], line_dash='dash',
                        line_color='grey', annotation_text=f"Meta {META_IA['MENSUAL']}")
    fig_comp.update_layout(
        height=360,
        margin=dict(l=20, r=20, t=30, b=80),
        xaxis=dict(categoryorder='array', categoryarray=MESES_ORDEN, title=''),
        yaxis=dict(title='ÍA Mensual', gridcolor='#E8EDF5'),
        plot_bgcolor='white', paper_bgcolor='white',
        legend=dict(orientation='h', y=-0.3)
    )
    st.plotly_chart(fig_comp, use_container_width=True)
elif not comp.empty:
    st.caption("Carga datos de más de un año para ver el comparativo anual.")
