"""
app.py — Punto de entrada del Sistema de Ausentismo DAP-SSMC
Define la navegacion y etiquetas del menu lateral.
"""
import streamlit as st

st.set_page_config(
    page_title="Ausentismo DAP-SSMC",
    page_icon="\U0001f3e5",
    layout="wide",
    initial_sidebar_state="expanded",
)

pg = st.navigation([
    st.Page("pages/0_\U0001f3e0_INICIO.py",         title="INICIO",           icon="\U0001f3e0", default=True),
    st.Page("pages/1_\U0001f4ca_Dashboard.py",       title="Dashboard",        icon="\U0001f4ca"),
    st.Page("pages/2_\U0001f3e5_Por_CESFAM.py",      title="Por CESFAM",       icon="\U0001f3e5"),
    st.Page("pages/3_\U0001f464_Por_Funcionario.py", title="Por Funcionario",  icon="\U0001f464"),
    st.Page("pages/4_\U0001f4cb_Gestion_Casos.py",   title="Gestion Casos",    icon="\U0001f4cb"),
    st.Page("pages/5_\U0001f4c4_Reportes.py",        title="Reportes",         icon="\U0001f4c4"),
    st.Page("pages/6_\U0001f4e5_Cargar_Datos.py",    title="Cargar Datos",     icon="\U0001f4e5"),
    st.Page("pages/7_\U0001f4ca_Comparativo.py",     title="Comparativo",      icon="\U0001f4ca"),
])
pg.run()
