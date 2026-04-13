"""
Estado del Programa de Gestión de Casos — Acompañamiento, COMPIN, etc.
"""
import streamlit as st
from modules.sidebar_css import inject as _inject_css
import plotly.express as px
import pandas as pd
from modules.db import get_gestion_casos, init_db, get_catalogo
from modules.ui import show_table

init_db()
_inject_css()

st.title("📋 Gestión de Casos de Ausentismo")
st.divider()

with st.sidebar:
    st.markdown("### 🔍 Filtros")
    sel_vigente  = st.selectbox("Vigencia", ['Todos','VIGENTE','NO VIGENTE'])
    sel_proceso  = st.multiselect("Estado de proceso",
                                    ['ACOMPAÑAMIENTO','COMPIN','CONTACTAR','ENVIO CARTA',
                                     'CATASTRÓFICO','SIN ACCIONES','NO VIGENTE'])
    sel_estab    = st.multiselect("Establecimiento",
                                    get_catalogo('gestion_casos','establecimiento'))
    sel_resp     = st.multiselect("Responsable",
                                    get_catalogo('gestion_casos','responsable'))

@st.cache_data(ttl=60)
def cargar():
    return get_gestion_casos()

df = cargar()

if df.empty:
    st.warning("Sin datos de gestión. Carga el archivo BASE AUSENTISMO en 📥 Cargar Datos.")
    st.stop()

# Aplicar filtros
if sel_vigente != 'Todos':
    df = df[df['vigente'].str.upper().str.contains(sel_vigente.upper(), na=False)]
if sel_proceso:
    df = df[df['proceso'].str.upper().isin([p.upper() for p in sel_proceso])]
if sel_estab:
    df = df[df['establecimiento'].isin(sel_estab)]
if sel_resp:
    df = df[df['responsable'].isin(sel_resp)]

# ── KPIs ────────────────────────────────────────────────────────────────
vig    = (df['vigente'].str.upper().str.strip() == 'VIGENTE').sum()
no_vig = (df['vigente'].str.upper().str.strip() == 'NO VIGENTE').sum()
compin = (df['proceso'].str.upper().str.contains('COMPIN', na=False)).sum()
acomp  = (df['proceso'].str.upper().str.contains('ACOMP', na=False)).sum()
catast = (df['proceso'].str.upper().str.contains('CATASTR', na=False)).sum()
sin_acc= (df['proceso'].str.upper().str.contains('SIN ACCION', na=False)).sum()

col1,col2,col3,col4,col5,col6 = st.columns(6)
col1.metric("Total registros", len(df))
col2.metric("✅ Vigentes", vig)
col3.metric("❌ No vigentes", no_vig)
col4.metric("🔴 En COMPIN", compin)
col5.metric("🟠 Acompañamiento", acomp)
col6.metric("🟣 Catastróficos", catast)

st.divider()

# ── Gráficos ──────────────────────────────────────────────────────────────
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("📊 Estado de Proceso")
    proc_cnt = df['proceso'].value_counts().reset_index()
    proc_cnt.columns = ['proceso','n']
    fig = px.bar(proc_cnt, x='n', y='proceso', orientation='h',
                 color='n', color_continuous_scale=['#D6E8F7','#006FB9','#00386B'],
                 text='n')
    fig.update_traces(textposition='outside')
    fig.update_layout(height=350, showlegend=False, coloraxis_showscale=False,
                      margin=dict(l=10,r=40,t=20,b=20))
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.subheader("🏥 Por Establecimiento")
    est_cnt = df[df['vigente'].str.upper().str.strip()=='VIGENTE'].groupby(
        'establecimiento').size().reset_index(name='n').sort_values('n', ascending=False)
    fig = px.bar(est_cnt, x='n', y='establecimiento', orientation='h',
                 color_discrete_sequence=['#006FB9'], text='n')
    fig.update_traces(textposition='outside')
    fig.update_layout(height=350, showlegend=False,
                      margin=dict(l=10,r=40,t=20,b=20))
    st.plotly_chart(fig, use_container_width=True)

# ── Tabla detalle ─────────────────────────────────────────────────────────
st.subheader("📄 Listado de Casos")
tabs = st.tabs(["Casos Vigentes", "En COMPIN", "Acompañamiento Activo", "Catastróficos", "Todos"])

def mostrar_tabla(df_sub):
    cols = ['rut','nombre','vigente','proceso','establecimiento','estamento',
            'compin','responsable','carta','ult_ausentismo','aus_ajustado']
    cols = [c for c in cols if c in df_sub.columns]
    show_table(df_sub[cols].rename(columns={
        'rut':'RUT','nombre':'Nombre','vigente':'Vigente','proceso':'Proceso',
        'establecimiento':'CESFAM','estamento':'Estamento',
        'compin':'COMPIN','responsable':'Responsable',
        'carta':'Carta','ult_ausentismo':'Últ.Aus.','aus_ajustado':'Aus.Ajust.'
    }))

with tabs[0]:
    vigentes = df[df['vigente'].str.upper().str.strip()=='VIGENTE']
    mostrar_tabla(vigentes)

with tabs[1]:
    en_compin = df[df['proceso'].str.upper().str.contains('COMPIN', na=False)]
    mostrar_tabla(en_compin)

with tabs[2]:
    en_acomp = df[df['proceso'].str.upper().str.contains('ACOMP', na=False)]
    mostrar_tabla(en_acomp)

with tabs[3]:
    en_catast = df[df['proceso'].str.upper().str.contains('CATASTR', na=False)]
    mostrar_tabla(en_catast)

with tabs[4]:
    mostrar_tabla(df)

# ── Exportar ──────────────────────────────────────────────────────────────
csv = df.to_csv(index=False).encode('utf-8-sig')
st.download_button("⬇️ Exportar CSV completo", csv,
                    file_name="gestion_casos.csv", mime='text/csv')
