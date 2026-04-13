"""
Análisis Comparativo — ÍA por centro, planta, edad, género, día de semana
Replica los análisis del cuadro de mando Excel de la DAP-SSMC.
"""
import streamlit as st
from modules.sidebar_css import inject as _inject_css
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from modules.db import get_catalogo, get_periodo, init_db
from modules.metrics import (
    build_df, kpis_por_cesfam, comparativo_anual_mensual,
    ia_mensual_por_cesfam, distribucion_edad_cesfam,
    ia_por_genero, ia_por_planta, dist_dia_semana_por_cesfam,
    META_IA, fmt_peso, fmt_num, DOTACION_PROMEDIO
)
from modules.ui import show_table

init_db()
_inject_css()

# ── CSS ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  h1,h2,h3 { color: #00386B; }
  .stTabs [data-baseweb="tab"] { font-size: 0.9rem; font-weight: 600; }
</style>""", unsafe_allow_html=True)

st.title("📊 Análisis Comparativo — DAP-SSMC")
st.caption("Índice de Ausentismo por centro, planta, edad, género y día de semana.")
st.divider()

# ── Sidebar filtros ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔍 Filtros")
    unidades = get_catalogo('licencias', 'nombre_unidad')
    plantas  = get_catalogo('licencias', 'planta')
    periodo  = get_periodo()

    sel_u = st.multiselect("Establecimientos", unidades, placeholder="Todos")
    sel_p = st.multiselect("Planta / Estamento", plantas, placeholder="Todas")
    fi    = st.text_input("Desde (YYYY-MM-DD)", value=periodo[0] or '')
    ff    = st.text_input("Hasta (YYYY-MM-DD)", value=periodo[1] or '')
    dot   = st.number_input("Dotación promedio", value=DOTACION_PROMEDIO, step=10,
                             help="Denominador para calcular el ÍA")
    meta  = st.number_input("Meta ÍA anual (IV Corte)", value=META_IA['IV_CORTE'],
                             step=0.01, format="%.2f")

# ── Carga ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner="Calculando indicadores...")
def cargar(u, p, fi, ff, d):
    return build_df(
        unidades=u or None, plantas=p or None,
        fecha_ini=fi or None, fecha_fin=ff or None, excluir_cgr=True
    )

df = cargar(tuple(sel_u), tuple(sel_p), fi, ff, dot)

if df.empty:
    st.warning("Sin datos. Carga los archivos en 📥 Cargar Datos.")
    st.stop()

# ── Tabs ──────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🏥 ÍA por Centro",
    "📅 Comparativo Anual",
    "👶 Por Edad",
    "⚥ Por Género",
    "🏢 Por Planta",
    "📆 Día de Semana",
])


# ══════════════════════════════════════════════════════════════════════════
# TAB 1 — ÍA POR CENTRO con línea meta
# ══════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("Índice de Ausentismo Acumulado por Centro")

    cesfam_df = kpis_por_cesfam(df, dot)

    if cesfam_df.empty:
        st.info("Sin datos suficientes.")
    else:
        # ── Gráfico barras + línea meta ────────────────────────────────
        fig = go.Figure()
        colores_barra = [
            '#1E8B4C' if s == 'VERDE' else '#FFC000' if s == 'AMARILLO' else '#C00000'
            for s in cesfam_df['semaforo']
        ]
        fig.add_trace(go.Bar(
            x=cesfam_df['cesfam'],
            y=cesfam_df['ia_acumulado'],
            marker_color=colores_barra,
            text=[f"{v:.2f}" for v in cesfam_df['ia_acumulado']],
            textposition='outside',
            textfont=dict(size=11),
            name='ÍA Acumulado 2026',
            hovertemplate='<b>%{x}</b><br>ÍA: %{y:.2f}<extra></extra>'
        ))
        fig.add_hline(
            y=meta, line_dash='solid', line_color='#C00000', line_width=2,
            annotation_text=f"Máx. IV Corte {meta:.2f}",
            annotation_font_color='#C00000',
            annotation_position='top right'
        )
        fig.update_layout(
            title=f"ÍNDICE DE AUSENTISMO POR CENTRO — {fi or ''} al {ff or ''}",
            title_font=dict(size=14, color='#00386B'),
            height=480,
            margin=dict(l=20, r=20, t=60, b=100),
            xaxis_tickangle=-30,
            xaxis_title='',
            yaxis_title='Índice de Ausentismo',
            plot_bgcolor='white', paper_bgcolor='white',
            showlegend=True,
            legend=dict(orientation='h', y=-0.35),
            yaxis=dict(gridcolor='#E8EDF5')
        )
        st.plotly_chart(fig, use_container_width=True)

        # ── ÍA mensual por CESFAM (mapa de calor) ──────────────────────
        st.subheader("Índice Mensual por Centro (Mapa de Calor)")
        pivot = ia_mensual_por_cesfam(df, dot)
        if not pivot.empty:
            fig2 = px.imshow(
                pivot,
                color_continuous_scale=[
                    [0.00, '#D6F5E3'], [0.40, '#FFF9C4'],
                    [0.65, '#FFD700'], [1.00, '#C00000']
                ],
                aspect='auto',
                labels=dict(x='Período', y='Centro de Salud', color='ÍA'),
                zmin=0, zmax=max(pivot.values.max(), 3.5)
            )
            fig2.update_traces(
                text=pivot.values.round(2),
                texttemplate='%{text}',
                textfont=dict(size=9)
            )
            fig2.update_layout(
                height=max(350, 35 * len(pivot)),
                margin=dict(l=20, r=20, t=40, b=60),
                coloraxis_colorbar=dict(title='ÍA')
            )
            st.plotly_chart(fig2, use_container_width=True)

        # ── Tabla resumen ──────────────────────────────────────────────
        st.subheader("Tabla Resumen por Centro")
        disp = cesfam_df.copy()
        disp['Semáforo'] = disp['semaforo'].apply(
            lambda s: f"{'🟢' if s=='VERDE' else '🟡' if s=='AMARILLO' else '🔴'} {s}"
        )
        disp['Costo'] = disp['costo_total'].apply(lambda x: fmt_peso(x))
        disp['Días'] = disp['dias_total'].apply(fmt_num)
        disp['N° LM'] = disp['n_lm'].apply(fmt_num)
        disp = disp.rename(columns={
            'cesfam': 'Centro', 'n_funcionarios': 'Func.',
            'ia_acumulado': 'ÍA Acum.', 'ia_mensual': 'ÍA Mes',
            'tasa_frecuencia': 'TF', 'tasa_gravedad': 'TG',
            'pct_corto': '% Corta', 'pct_prolongado': '% Prolong.',
            'n_recurrentes_5': 'Recur ≥5'
        })
        cols = ['Centro', 'N° LM', 'Días', 'Func.', 'ÍA Acum.', 'ÍA Mes',
                'TF', 'TG', '% Corta', '% Prolong.', 'Recur ≥5', 'Costo', 'Semáforo']
        show_table(disp[[c for c in cols if c in disp.columns]])


# ══════════════════════════════════════════════════════════════════════════
# TAB 2 — COMPARATIVO ANUAL MENSUAL
# ══════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Índice de Ausentismo Comparativo — Multi-año")
    comp = comparativo_anual_mensual(df, dot)

    if comp.empty:
        st.info("Sin datos para comparativo anual.")
    else:
        años = sorted(comp['anio'].unique())
        COLORES_ANIO = {
            años[0] if len(años) > 0 else 2024: '#C00000',
            años[1] if len(años) > 1 else 2025: '#FFC000',
            años[2] if len(años) > 2 else 2026: '#1E8B4C',
        }
        MESES_ORDEN = ['ENE','FEB','MAR','ABR','MAY','JUN',
                       'JUL','AGO','SEP','OCT','NOV','DIC']

        fig = go.Figure()
        for anio in años:
            sub = comp[comp['anio'] == anio].copy()
            sub = sub.sort_values('mes')
            color = COLORES_ANIO.get(anio, '#006FB9')
            fig.add_trace(go.Scatter(
                x=sub['mes_nom'],
                y=sub['ia'],
                mode='lines+markers',
                name=str(anio),
                line=dict(color=color, width=2.5),
                marker=dict(size=8),
                text=[f"{v:.2f}" for v in sub['ia']],
                textposition='top center',
                hovertemplate=f"<b>{anio} %{{x}}</b><br>ÍA: %{{y:.3f}}<extra></extra>"
            ))

        fig.add_hline(
            y=META_IA['MENSUAL'], line_dash='dash', line_color='grey',
            annotation_text=f"Meta mensual {META_IA['MENSUAL']}"
        )
        fig.update_layout(
            title="ÍNDICE DE AUSENTISMO COMPARATIVO ANUAL",
            title_font=dict(size=14, color='#00386B'),
            height=430,
            margin=dict(l=20, r=20, t=60, b=80),
            xaxis=dict(
                categoryorder='array', categoryarray=MESES_ORDEN,
                title='Mes'
            ),
            yaxis=dict(title='ÍA Mensual (días/func)', gridcolor='#E8EDF5'),
            plot_bgcolor='white', paper_bgcolor='white',
            legend=dict(orientation='h', y=-0.25)
        )
        st.plotly_chart(fig, use_container_width=True)

        # Tabla de valores
        st.subheader("Valores mensuales por año")
        pivot_comp = comp.pivot(index='mes_nom', columns='anio', values='ia').reindex(MESES_ORDEN)
        pivot_comp.columns = [str(c) for c in pivot_comp.columns]
        pivot_comp.index.name = 'Mes'
        pivot_comp = pivot_comp.round(2).reset_index()
        show_table(pivot_comp)

        # ÍA acumulado comparativo (barras agrupadas por año)
        st.subheader("ÍA Acumulado por Año (I Corte — hasta mes actual)")
        acum = comp.groupby('anio').agg(
            dias_total=('dias', 'sum'), n_lm=('n_lm', 'sum')
        ).reset_index()
        acum['ia_acum'] = (acum['dias_total'] / dot).round(2)
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=acum['anio'].astype(str),
            y=acum['ia_acum'],
            marker_color=['#C00000' if a < max(años) else '#006FB9'
                          for a in acum['anio']],
            text=[f"{v:.2f}" for v in acum['ia_acum']],
            textposition='outside',
            name='ÍA Acumulado'
        ))
        fig2.add_hline(y=meta, line_dash='solid', line_color='#C00000',
                        annotation_text=f"Máx. IV Corte {meta:.2f}",
                        annotation_font_color='#C00000')
        fig2.update_layout(
            title="ÍNDICE COMPARATIVO ACUMULADO",
            title_font=dict(size=14, color='#00386B'),
            height=360,
            margin=dict(l=20, r=20, t=60, b=60),
            xaxis_title='Año', yaxis_title='ÍA Acumulado',
            plot_bgcolor='white', paper_bgcolor='white',
            yaxis=dict(gridcolor='#E8EDF5')
        )
        st.plotly_chart(fig2, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════
# TAB 3 — POR EDAD
# ══════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Licencias Médicas por Tramo Etario y Centro de Salud")
    edad_df = distribucion_edad_cesfam(df)

    if edad_df.empty:
        st.info("Sin datos de edad.")
    else:
        TRAMOS = ['18-32 años', '33-52 años', '53+ años']
        COLORES_TRAMO = {'18-32 años': '#5B9BD5', '33-52 años': '#ED7D31', '53+ años': '#A5A5A5'}

        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("**N° de LM por tramo etario y centro**")
            pivot_edad = (edad_df.pivot(index='cesfam', columns='tramo', values='n_lm')
                          .reindex(columns=TRAMOS, fill_value=0).reset_index())
            fig = go.Figure()
            for tramo in TRAMOS:
                if tramo in pivot_edad.columns:
                    fig.add_trace(go.Bar(
                        name=tramo, x=pivot_edad['cesfam'], y=pivot_edad[tramo],
                        text=pivot_edad[tramo],
                        textposition='auto',
                        marker_color=COLORES_TRAMO[tramo]
                    ))
            fig.update_layout(
                barmode='group', height=420,
                title="LM por Edad y Centro",
                title_font=dict(size=13, color='#00386B'),
                margin=dict(l=10, r=10, t=50, b=120),
                xaxis_tickangle=-30, xaxis_title='',
                yaxis_title='N° LM', plot_bgcolor='white',
                legend=dict(orientation='h', y=-0.45)
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            st.markdown("**% por tramo etario y centro**")
            pivot_pct = (edad_df.pivot(index='cesfam', columns='tramo', values='pct')
                         .reindex(columns=TRAMOS, fill_value=0).reset_index())
            fig2 = go.Figure()
            for tramo in TRAMOS:
                if tramo in pivot_pct.columns:
                    fig2.add_trace(go.Bar(
                        name=tramo, x=pivot_pct['cesfam'], y=pivot_pct[tramo],
                        text=[f"{v:.0f}%" for v in pivot_pct[tramo]],
                        textposition='auto',
                        marker_color=COLORES_TRAMO[tramo]
                    ))
            fig2.update_layout(
                barmode='group', height=420,
                title="LICENCIAS MÉDICAS POR EDAD (%)",
                title_font=dict(size=13, color='#00386B'),
                margin=dict(l=10, r=10, t=50, b=120),
                xaxis_tickangle=-30, xaxis_title='',
                yaxis_title='%', plot_bgcolor='white',
                legend=dict(orientation='h', y=-0.45),
                yaxis=dict(ticksuffix='%')
            )
            st.plotly_chart(fig2, use_container_width=True)

        # Tabla resumen global
        st.subheader("Distribución global por tramo etario")
        global_edad = (edad_df.groupby('tramo')
                       .agg(n_lm=('n_lm', 'sum'))
                       .reindex(TRAMOS).reset_index())
        total = global_edad['n_lm'].sum()
        global_edad['%'] = (global_edad['n_lm'] / total * 100).round(1).astype(str) + '%'
        global_edad.columns = ['Tramo Etario', 'N° LM', '%']
        show_table(global_edad)

        # Tabla detalle por CESFAM
        st.subheader("Detalle por CESFAM y tramo")
        tbl = (edad_df.pivot_table(index='cesfam', columns='tramo',
                                   values='n_lm', aggfunc='sum', fill_value=0)
               .reindex(columns=TRAMOS, fill_value=0))
        tbl.columns.name = None
        tbl.index.name = 'CESFAM'
        tbl['TOTAL'] = tbl.sum(axis=1)
        for t in TRAMOS:
            if t in tbl.columns:
                tbl[f'% {t}'] = (tbl[t] / tbl['TOTAL'] * 100).round(0).astype(int).astype(str) + '%'
        show_table(tbl.reset_index())


# ══════════════════════════════════════════════════════════════════════════
# TAB 4 — POR GÉNERO
# ══════════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("Índice de Ausentismo según Dotación por Género")
    genero_df = ia_por_genero(df, dot)

    if genero_df.empty:
        st.info("Sin datos de género.")
    else:
        COLORES_GENERO = {'FEMENINO': '#5B9BD5', 'MASCULINO': '#ED7D31',
                          'F': '#5B9BD5', 'M': '#ED7D31'}

        col1, col2 = st.columns(2)
        with col1:
            # Torta días
            fig = px.pie(
                genero_df, values='dias', names='genero',
                color='genero', color_discrete_map=COLORES_GENERO,
                title="Distribución Días de Ausentismo por Género"
            )
            fig.update_traces(
                texttemplate='%{label}<br>%{value:,d} días<br>%{percent:.0%}',
                textfont_size=11
            )
            fig.update_layout(height=360, showlegend=True,
                              title_font=dict(color='#00386B'),
                              margin=dict(l=10, r=10, t=50, b=10))
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Barras ÍA por género
            fig2 = go.Figure()
            for _, row in genero_df.iterrows():
                g = str(row['genero'])
                fig2.add_trace(go.Bar(
                    x=[g], y=[row['ia']],
                    name=g,
                    marker_color=COLORES_GENERO.get(g.upper(), '#006FB9'),
                    text=[f"{row['ia']:.2f}"],
                    textposition='outside',
                    textfont=dict(size=14)
                ))
            fig2.update_layout(
                title="ÍNDICE DE AUSENTISMO SEGÚN DOTACIÓN",
                title_font=dict(size=13, color='#00386B'),
                height=360,
                margin=dict(l=20, r=20, t=60, b=40),
                showlegend=False,
                xaxis_title='Género', yaxis_title='ÍA (días/dotación)',
                plot_bgcolor='white', paper_bgcolor='white',
                yaxis=dict(gridcolor='#E8EDF5')
            )
            st.plotly_chart(fig2, use_container_width=True)

        # Tabla resumen género
        tbl_g = genero_df.copy()
        tbl_g['Días'] = tbl_g['dias'].apply(fmt_num)
        tbl_g['N° LM'] = tbl_g['n_lm'].apply(fmt_num)
        tbl_g['Costo'] = tbl_g['costo'].apply(lambda x: fmt_peso(x))
        tbl_g['Dotación ref.'] = tbl_g['dot_ref'].apply(fmt_num)
        tbl_g = tbl_g.rename(columns={
            'genero': 'Género', 'n_func': 'N° Func.',
            'pct_dias': '% Días', 'ia': 'ÍA', 'tg': 'TG'
        })
        show_table(tbl_g[['Género', 'N° LM', 'Días', '% Días', 'N° Func.',
                           'ÍA', 'TG', 'Dotación ref.', 'Costo']])


# ══════════════════════════════════════════════════════════════════════════
# TAB 5 — POR PLANTA / ESTAMENTO
# ══════════════════════════════════════════════════════════════════════════
with tab5:
    st.subheader("Índice de Ausentismo por Planta / Estamento")
    planta_df = ia_por_planta(df, dot)

    if planta_df.empty:
        st.info("Sin datos de planta.")
    else:
        COLORES_PLANTA = [
            '#1F4E79','#2E75B6','#5BA3C9','#9DC3E6',
            '#BDD7EE','#17375E','#31849B','#00B0F0'
        ]

        col1, col2 = st.columns([3, 2])
        with col1:
            fig = go.Figure()
            for i, (_, row) in enumerate(planta_df.iterrows()):
                fig.add_trace(go.Bar(
                    x=[row['planta']], y=[row['ia']],
                    name=row['planta'],
                    marker_color=COLORES_PLANTA[i % len(COLORES_PLANTA)],
                    text=[f"{row['ia']:.2f}"],
                    textposition='outside',
                    textfont=dict(size=10),
                    hovertemplate=(
                        f"<b>{row['planta']}</b><br>"
                        f"ÍA: {row['ia']:.2f}<br>"
                        f"Días: {int(row['dias']):,}<br>"
                        f"N° LM: {int(row['n_lm']):,}<extra></extra>"
                    )
                ))
            fig.update_layout(
                title="ÍNDICE DE AUSENTISMO POR PLANTA",
                title_font=dict(size=14, color='#00386B'),
                height=450,
                margin=dict(l=20, r=20, t=60, b=100),
                showlegend=False,
                xaxis_tickangle=-30,
                xaxis_title='',
                yaxis_title='ÍA (días/dotación)',
                plot_bgcolor='white', paper_bgcolor='white',
                yaxis=dict(gridcolor='#E8EDF5')
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("**Resumen por planta**")
            tbl_p = planta_df.copy()
            tbl_p['Días'] = tbl_p['dias'].apply(fmt_num)
            tbl_p['N° LM'] = tbl_p['n_lm'].apply(fmt_num)
            tbl_p['Costo'] = tbl_p['costo'].apply(lambda x: fmt_peso(x))
            tbl_p['Dot. ref.'] = tbl_p['dot_ref'].apply(fmt_num)
            tbl_p = tbl_p.rename(columns={
                'planta': 'Planta', 'n_func': 'N° Func.',
                'pct_dias': '% Días', 'ia': 'ÍA', 'tg': 'TG'
            })
            show_table(tbl_p[['Planta', 'N° LM', 'Días', '% Días',
                               'ÍA', 'TG', 'Dot. ref.', 'Costo']])

        # Tabla de días totales × CESFAM × Planta
        st.subheader("Total días LM por Planta y Centro de Salud")
        if 'nombre_unidad' in df.columns and 'planta' in df.columns:
            pivot_p = (df.groupby(['planta', 'nombre_unidad'])['dias_periodo']
                       .sum().unstack(fill_value=0))
            pivot_p['TOTAL'] = pivot_p.sum(axis=1)
            pivot_p = pivot_p.sort_values('TOTAL', ascending=False)
            pivot_p.index.name = 'Planta'
            pivot_p.columns.name = None
            # Formatear con separador de miles
            pf = pivot_p.applymap(lambda x: f"{int(x):,}" if x > 0 else '0')
            show_table(pf.reset_index())


# ══════════════════════════════════════════════════════════════════════════
# TAB 6 — DÍA DE LA SEMANA POR CESFAM
# ══════════════════════════════════════════════════════════════════════════
with tab6:
    st.subheader("Inicio de Licencias Médicas por Día de la Semana")
    dia_c = dist_dia_semana_por_cesfam(df)

    if dia_c.empty:
        st.info("Sin datos.")
    else:
        DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        COLORES_DIA = [
            '#1F4E79','#2E75B6','#5BA3C9','#9DC3E6',
            '#BDD7EE','#C00000','#FFC000'
        ]

        # Barras apiladas día × cesfam
        fig = go.Figure()
        cesfams = dia_c.index.tolist()
        for i, dia in enumerate([d for d in DIAS if d in dia_c.columns]):
            fig.add_trace(go.Bar(
                name=dia,
                x=cesfams,
                y=dia_c[dia].values,
                marker_color=COLORES_DIA[i % len(COLORES_DIA)],
                hovertemplate=f"<b>%{{x}}</b><br>{dia}: %{{y:,d}} LM<extra></extra>"
            ))
        fig.update_layout(
            barmode='group',
            title="LM POR DÍA DE INICIO Y CENTRO DE SALUD",
            title_font=dict(size=14, color='#00386B'),
            height=480,
            margin=dict(l=20, r=20, t=60, b=120),
            xaxis_tickangle=-30, xaxis_title='',
            yaxis_title='N° LM', plot_bgcolor='white',
            paper_bgcolor='white',
            legend=dict(orientation='h', y=-0.4),
            yaxis=dict(gridcolor='#E8EDF5')
        )
        st.plotly_chart(fig, use_container_width=True)

        # Barras globales
        st.subheader("Distribución global por día de semana")
        global_dia = dia_c.sum().reset_index()
        global_dia.columns = ['Día', 'N° LM']
        global_dia = global_dia[global_dia['Día'].isin(DIAS)]
        global_dia['%'] = (global_dia['N° LM'] / global_dia['N° LM'].sum() * 100).round(1)

        col1, col2 = st.columns([2, 1])
        with col1:
            fig2 = px.bar(
                global_dia, x='Día', y='N° LM',
                text='%',
                color_discrete_sequence=['#006FB9']
            )
            fig2.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig2.update_layout(
                height=320, showlegend=False,
                margin=dict(l=10, r=10, t=20, b=40),
                plot_bgcolor='white', xaxis_title='',
                yaxis=dict(title='N° LM', gridcolor='#E8EDF5')
            )
            st.plotly_chart(fig2, use_container_width=True)
        with col2:
            global_dia['N° LM'] = global_dia['N° LM'].apply(lambda x: f"{int(x):,}")
            global_dia['%'] = global_dia['%'].astype(str) + '%'
            show_table(global_dia)

        # Tabla pivot
        st.subheader("Detalle: N° LM por CESFAM y día de la semana")
        dias_disp = [d for d in DIAS if d in dia_c.columns]
        tbl_dia = dia_c[dias_disp].copy()
        tbl_dia['TOTAL'] = tbl_dia.sum(axis=1)
        tbl_dia = tbl_dia.reset_index()
        # Formato números
        for col in tbl_dia.columns[1:]:
            tbl_dia[col] = tbl_dia[col].apply(lambda x: f"{int(x):,}" if x > 0 else '0')
        show_table(tbl_dia)
