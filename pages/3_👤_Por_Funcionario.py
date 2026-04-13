"""
Análisis por funcionario individual — búsqueda, ranking, semáforo
"""
import streamlit as st
import plotly.express as px
import pandas as pd
from modules.db import get_catalogo, get_periodo, init_db, query_df
from modules.metrics import (
    build_df, kpis_por_funcionario, analisis_recurrencia,
    semaforo_funcionario, emoji_semaforo, color_semaforo, SEMAFORO_COLORES
)
from modules.ui import show_table

st.set_page_config(page_title="Por Funcionario | Ausentismo", page_icon="👤", layout="wide")
init_db()

st.title("👤 Análisis por Funcionario")
st.divider()

# ── Sidebar ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔍 Filtros")
    unidades  = get_catalogo('licencias', 'nombre_unidad')
    plantas   = get_catalogo('licencias', 'planta')
    generos   = get_catalogo('licencias', 'genero')
    calidades = get_catalogo('licencias', 'calidad_juridica')
    periodo   = get_periodo()

    sel_u = st.multiselect("Establecimiento", unidades, placeholder="Todos")
    sel_p = st.multiselect("Planta", plantas, placeholder="Todas")
    sel_g = st.multiselect("Género", generos, placeholder="Todos")
    sel_c = st.multiselect("Calidad jurídica", calidades, placeholder="Todas")
    fi    = st.text_input("Desde", value=periodo[0] or '')
    ff    = st.text_input("Hasta", value=periodo[1] or '')

    st.divider()
    filtro_sem = st.multiselect("Filtrar por semáforo",
                                 ['ROJO','NARANJA','AMARILLO','VERDE'],
                                 default=['ROJO','NARANJA'])

@st.cache_data(ttl=120, show_spinner="Calculando...")
def cargar(u, p, g, c, fi, ff):
    df = build_df(unidades=u or None, plantas=p or None, generos=g or None,
                  calidades=c or None, fecha_ini=fi or None, fecha_fin=ff or None)
    return df

df = cargar(tuple(sel_u), tuple(sel_p), tuple(sel_g),
            tuple(sel_c), fi, ff)

if df.empty:
    st.warning("Sin datos. Carga los archivos en 📥 Cargar Datos.")
    st.stop()

func_df = kpis_por_funcionario(df)

# ── Tabs ───────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🚦 Ranking y Semáforo", "🔎 Búsqueda Individual", "📈 Recurrencia"])

# ── Tab 1: Ranking ─────────────────────────────────────────────────────────
with tab1:
    col_a, col_b, col_c, col_d, col_e = st.columns(5)
    total = len(func_df)
    n_rojo    = (func_df['semaforo']=='ROJO').sum()   if 'semaforo' in func_df.columns else 0
    n_naranja = (func_df['semaforo']=='NARANJA').sum() if 'semaforo' in func_df.columns else 0
    n_amarillo= (func_df['semaforo']=='AMARILLO').sum() if 'semaforo' in func_df.columns else 0
    n_verde   = (func_df['semaforo']=='VERDE').sum()  if 'semaforo' in func_df.columns else 0

    col_a.metric("Total funcionarios", total)
    col_b.metric("🔴 Crítico/Rojo",    n_rojo)
    col_c.metric("🟠 Naranja",         n_naranja)
    col_d.metric("🟡 Amarillo",        n_amarillo)
    col_e.metric("🟢 Verde",           n_verde)

    # Gráfico semáforo
    if 'semaforo' in func_df.columns:
        sem_cnt = func_df['semaforo'].value_counts().reset_index()
        sem_cnt.columns = ['semaforo', 'n']
        sem_cnt['color'] = sem_cnt['semaforo'].map(SEMAFORO_COLORES)
        fig = px.bar(sem_cnt, x='semaforo', y='n', color='semaforo',
                     color_discrete_map=SEMAFORO_COLORES,
                     text='n', title='Distribución de Funcionarios por Semáforo')
        fig.update_traces(textposition='outside')
        fig.update_layout(height=300, showlegend=False,
                          margin=dict(l=10,r=10,t=40,b=20))
        st.plotly_chart(fig, use_container_width=True)

    # Tabla filtrada por semáforo
    st.subheader("Funcionarios por nivel de alerta")
    if filtro_sem and 'semaforo' in func_df.columns:
        filtrado = func_df[func_df['semaforo'].isin(filtro_sem)].copy()
    else:
        filtrado = func_df.copy()

    if 'semaforo' in filtrado.columns:
        filtrado['Semáforo'] = filtrado['semaforo'].apply(
            lambda s: f"{emoji_semaforo(s)} {s}")

    cols_show = ['rut','nombre','unidad','planta','genero',
                 'n_lm_total','dias_total','costo_total','tg',
                 'n_lm_ult_anio','Semáforo']
    cols_show = [c for c in cols_show if c in filtrado.columns]

    if 'proceso' in filtrado.columns:
        cols_show.append('proceso')

    show_table(
        filtrado[cols_show].rename(columns={
            'rut':'RUT','nombre':'Nombre','unidad':'CESFAM',
            'planta':'Planta','genero':'Género',
            'n_lm_total':'N° LM','dias_total':'Días',
            'costo_total':'Costo','tg':'TG',
            'n_lm_ult_anio':'LM últ.año','proceso':'Proceso'
        })
    )

    # Exportar CSV
    csv_data = filtrado.to_csv(index=False).encode('utf-8-sig')
    st.download_button("⬇️ Descargar CSV", csv_data,
                        file_name="funcionarios_ausentismo.csv",
                        mime='text/csv')

# ── Tab 2: Búsqueda individual ────────────────────────────────────────────
with tab2:
    st.subheader("🔎 Ficha Individual de Funcionario")
    busq = st.text_input("Buscar por RUT o nombre")

    if busq:
        busq_lower = busq.strip().lower()
        mask = (func_df['nombre'].str.lower().str.contains(busq_lower, na=False) |
                func_df['rut'].astype(str).str.contains(busq_lower, na=False))
        resultados = func_df[mask]

        if resultados.empty:
            st.info("No se encontraron resultados.")
        else:
            if len(resultados) > 1:
                nombres = resultados['nombre'].tolist()
                sel_nombre = st.selectbox("Selecciona funcionario", nombres)
                row = resultados[resultados['nombre'] == sel_nombre].iloc[0]
            else:
                row = resultados.iloc[0]

            # Ficha
            rut_sel = row['rut']
            sem = row.get('semaforo', 'VERDE')

            col1, col2 = st.columns([1, 2])
            with col1:
                color = color_semaforo(sem)
                st.markdown(f"""
                <div style="background:{color};color:white;padding:16px;border-radius:10px;text-align:center">
                  <div style="font-size:2.5rem">{emoji_semaforo(sem)}</div>
                  <div style="font-size:1rem;font-weight:bold">{sem}</div>
                </div>
                """, unsafe_allow_html=True)
                st.metric("N° LM total", row['n_lm_total'])
                st.metric("Días acumulados", int(row['dias_total']))
                st.metric("Costo total LM", f"${row['costo_total']:,.0f}")
                st.metric("Tasa Gravedad (días/LM)", row['tg'])

            with col2:
                st.markdown(f"### {row['nombre']}")
                st.markdown(f"- **RUT:** {rut_sel}")
                st.markdown(f"- **Establecimiento:** {row.get('unidad','')}")
                st.markdown(f"- **Planta:** {row.get('planta','')}")
                st.markdown(f"- **Género:** {row.get('genero','')}")
                st.markdown(f"- **Calidad jurídica:** {row.get('calidad','')}")
                if 'proceso' in row: st.markdown(f"- **Estado gestión:** {row['proceso']}")
                if 'responsable' in row: st.markdown(f"- **Responsable:** {row['responsable']}")
                st.markdown(f"- **LM último año:** {row.get('n_lm_ult_anio', '—')}")
                st.markdown(f"- **Último tipo LM:** {row.get('ult_tipo_lm','')}")
                ult = row.get('ult_fecha_lm')
                if ult:
                    st.markdown(f"- **Última LM:** {str(ult)[:10]}")

            # Historial completo de LM de este funcionario
            st.markdown("#### 📋 Historial completo de LM")
            hist = df[df['rut'] == rut_sel][
                ['fecha_inicio','fecha_termino','dias_periodo','tipo_lm','costo','nombre_unidad']
            ].sort_values('fecha_inicio', ascending=False)
            hist.columns = ['Inicio','Término','Días','Tipo LM','Costo','Unidad']
            show_table(hist)

            # Gráfico timeline
            if len(hist) > 0:
                hist_plot = df[df['rut'] == rut_sel].copy()
                hist_plot['fecha_inicio'] = pd.to_datetime(hist_plot['fecha_inicio'], errors='coerce')
                hist_plot = hist_plot.dropna(subset=['fecha_inicio'])
                if len(hist_plot) > 0:
                    fig = px.scatter(hist_plot, x='fecha_inicio', y='dias_periodo',
                                     color='tipo_lm', size='dias_periodo',
                                     title=f"Timeline de LM — {row['nombre']}",
                                     hover_data=['fecha_termino','costo'])
                    fig.update_layout(height=300, margin=dict(l=10,r=10,t=40,b=40))
                    st.plotly_chart(fig, use_container_width=True)

# ── Tab 3: Recurrencia ────────────────────────────────────────────────────
with tab3:
    st.subheader("🔄 Análisis de Recurrencia")
    rec_df = analisis_recurrencia(df)
    if not rec_df.empty:
        # Distribución por nivel
        nivel_cnt = rec_df.groupby('nivel').agg(
            n_func=('rut','count'), dias=('dias_total','sum')
        ).reset_index()
        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(nivel_cnt, x='nivel', y='n_func', text='n_func',
                         color_discrete_sequence=['#006FB9'],
                         title='Funcionarios por nivel de recurrencia')
            fig.update_traces(textposition='outside')
            fig.update_layout(height=300, margin=dict(l=10,r=10,t=40,b=20))
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.bar(nivel_cnt, x='nivel', y='dias', text='dias',
                         color_discrete_sequence=['#C00000'],
                         title='Días de ausentismo por nivel')
            fig.update_traces(texttemplate='%{text:,}', textposition='outside')
            fig.update_layout(height=300, margin=dict(l=10,r=10,t=40,b=20))
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Top 50 funcionarios más recurrentes")
        top_rec = rec_df.head(50)[['rut','nombre','unidad','planta','n_lm','dias_total','costo_total']].copy()
        top_rec.columns = ['RUT','Nombre','Unidad','Planta','N° LM','Días','Costo']
        top_rec['Semáforo'] = top_rec.apply(
            lambda r: f"{emoji_semaforo(semaforo_funcionario(r['Días'], r['N° LM']))} {semaforo_funcionario(r['Días'], r['N° LM'])}",
            axis=1
        )
        show_table(top_rec)
