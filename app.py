"""
app.py — Sistema de Seguimiento de Ausentismo DAP-SSMC
Punto de entrada Streamlit — página de inicio / estado del sistema
"""
import streamlit as st
from modules.db import init_db, get_stats

st.set_page_config(
    page_title="Ausentismo DAP-SSMC",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS global
st.markdown("""
<style>
  [data-testid="stSidebar"] { background: #00386B; }
  [data-testid="stSidebar"] * { color: white !important; }
  [data-testid="stSidebar"] .stRadio label { color: white !important; }
  .metric-card {
    background: white; border-radius: 10px; padding: 20px;
    text-align: center; box-shadow: 0 2px 10px rgba(0,0,0,.08);
    border-top: 4px solid #006FB9;
  }
  .metric-card .val { font-size: 2rem; font-weight: 700; color: #00386B; }
  .metric-card .lbl { font-size: .8rem; color: #666; margin-top: 4px; }
  .stAlert { border-radius: 8px; }
  h1, h2, h3 { color: #00386B; }
</style>
""", unsafe_allow_html=True)

# Inicializar BD
init_db()

# ── Sidebar ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🏥 DAP-SSMC")
    st.markdown("**Sistema de Ausentismo**")
    st.markdown("---")
    st.markdown("📌 **Navegación**")
    st.markdown("Usa el menú de páginas ↑")
    st.markdown("---")
    stats = get_stats()
    st.markdown(f"🗄️ **Base de datos**")
    st.markdown(f"- LM cargadas: **{stats['n_licencias']:,}**")
    st.markdown(f"- Dotación: **{stats['n_dotacion']:,}**")
    st.markdown(f"- Casos gestión: **{stats['n_gestion']:,}**")
    if stats['periodo_ini']:
        st.markdown(f"- Período: {stats['periodo_ini']} → {stats['periodo_fin']}")

# ── Contenido principal ───────────────────────────────────────────────────
st.title("🏥 Sistema de Seguimiento del Ausentismo Laboral")
st.markdown("**Dirección de Atención Primaria — Servicio de Salud Metropolitano Central**")
st.divider()

stats = get_stats()
tiene_datos = stats['n_licencias'] > 0

if not tiene_datos:
    st.warning("⚠️ **Sin datos cargados.** Ve a la página **Cargar Datos** para importar los archivos Excel.")
    st.stop()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Licencias Médicas", f"{stats['n_licencias']:,}", help="Total LM en la base de datos")
with col2:
    st.metric("Dotación registrada", f"{stats['n_dotacion']:,}")
with col3:
    st.metric("Casos en gestión", f"{stats['n_gestion']:,}")
with col4:
    st.metric("Cargas realizadas", f"{stats['n_cargas']}")

st.divider()
st.markdown("""
### 📋 Páginas disponibles

| Página | Descripción |
|---|---|
| 📊 **Dashboard** | KPIs globales, semáforo, tendencia mensual del ÍA |
| 🏥 **Por CESFAM** | Análisis granular por establecimiento con comparativo |
| 👤 **Por Funcionario** | Búsqueda individual, ranking y clasificación semáforo |
| 📋 **Gestión de Casos** | Estado del programa de acompañamiento y COMPIN |
| 📄 **Reportes** | Generar informe Word y HTML con filtros personalizados |
| 📥 **Cargar Datos** | Carga incremental de archivos Excel (dotación + LM) |
""")

if stats['periodo_ini']:
    st.info(f"📅 Período en base de datos: **{stats['periodo_ini']}** → **{stats['periodo_fin']}**")
