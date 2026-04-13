"""
Página de INICIO — Estado general del sistema y definición del semáforo
"""
import streamlit as st
from modules.sidebar_css import inject as _inject_css
from modules.db import init_db, get_stats

init_db()
_inject_css()

# ── CSS local ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
.sem-card {
    border-radius: 10px; padding: 14px 18px;
    margin-bottom: 6px; color: white;
    display: flex; align-items: flex-start; gap: 12px;
}
.sem-card .sem-icon { font-size: 1.6rem; line-height: 1; }
.sem-card .sem-title { font-size: 1rem; font-weight: 700; margin-bottom: 3px; }
.sem-card .sem-desc { font-size: 0.82rem; opacity: 0.93; line-height: 1.4; }
h1, h2, h3 { color: #00386B; }
</style>
""", unsafe_allow_html=True)

# ── Título ────────────────────────────────────────────────────────────────
st.title("🏥 Sistema de Seguimiento del Ausentismo Laboral")
st.markdown("**Dirección de Atención Primaria — Servicio de Salud Metropolitano Central**")
st.divider()

# ── KPIs de estado ────────────────────────────────────────────────────────
stats = get_stats()
tiene_datos = stats['n_licencias'] > 0

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Licencias Médicas", f"{stats['n_licencias']:,}", help="Total LM en la base de datos")
with col2:
    st.metric("Dotación registrada", f"{stats['n_dotacion']:,}")
with col3:
    st.metric("Casos en gestión", f"{stats['n_gestion']:,}")
with col4:
    st.metric("Cargas realizadas", f"{stats['n_cargas']}")

if stats['periodo_ini']:
    st.info(f"📅 Período en base de datos: **{stats['periodo_ini']}** → **{stats['periodo_fin']}**")

if not tiene_datos:
    st.warning("⚠️ **Sin datos cargados.** Ve a la página **Cargar Datos** para importar los archivos Excel.")

st.divider()

# ── Definición del Semáforo ───────────────────────────────────────────────
st.markdown("## 🚦 Definición del Sistema de Semáforo")
st.markdown("""
El sistema clasifica el nivel de ausentismo mediante dos semáforos independientes:
uno para **establecimientos (CESFAM)** basado en el Índice de Ausentismo mensual,
y otro para **funcionarios individuales** basado en días acumulados y número de LM.
""")

col_csf, col_func = st.columns(2)

with col_csf:
    st.markdown("### 🏥 Semáforo CESFAM")
    st.markdown("*Basado en el Índice de Ausentismo (ÍA) mensual — días LM / dotación*")
    st.markdown("""
<div class="sem-card" style="background:#1E8B4C;">
  <div class="sem-icon">🟢</div>
  <div>
    <div class="sem-title">VERDE — Dentro de meta</div>
    <div class="sem-desc">ÍA mensual ≤ 2,17<br>
    El establecimiento se encuentra dentro del umbral mensual aceptable.
    Meta anual IV Corte: ÍA ≤ 26,02</div>
  </div>
</div>
<div class="sem-card" style="background:#B8860B;">
  <div class="sem-icon">🟡</div>
  <div>
    <div class="sem-title">AMARILLO — Alerta</div>
    <div class="sem-desc">ÍA mensual entre 2,18 y 2,60<br>
    Supera la meta mensual. Se requiere monitoreo activo
    y revisión de funcionarios prioritarios.</div>
  </div>
</div>
<div class="sem-card" style="background:#C00000;">
  <div class="sem-icon">🔴</div>
  <div>
    <div class="sem-title">ROJO — Crítico</div>
    <div class="sem-desc">ÍA mensual > 2,60<br>
    Nivel crítico. Se activa el protocolo de intervención,
    revisión COMPIN y acciones de acompañamiento.</div>
  </div>
</div>
""", unsafe_allow_html=True)

with col_func:
    st.markdown("### 👤 Semáforo Funcionario")
    st.markdown("*Basado en días de LM acumulados y número de licencias en el período*")
    st.markdown("""
<div class="sem-card" style="background:#1E8B4C;">
  <div class="sem-icon">🟢</div>
  <div>
    <div class="sem-title">VERDE — Sin riesgo</div>
    <div class="sem-desc">Días acumulados &lt; 30 <b>Y</b> N° LM &lt; 3<br>
    Ausencias dentro del rango esperado para el período.</div>
  </div>
</div>
<div class="sem-card" style="background:#B8860B;">
  <div class="sem-icon">🟡</div>
  <div>
    <div class="sem-title">AMARILLO — Seguimiento</div>
    <div class="sem-desc">Días ≥ 30 <b>O</b> N° LM ≥ 3<br>
    Funcionario con ausentismo moderado. Se recomienda
    entrevista de seguimiento.</div>
  </div>
</div>
<div class="sem-card" style="background:#FF6600;">
  <div class="sem-icon">🟠</div>
  <div>
    <div class="sem-title">NARANJA — Prioritario</div>
    <div class="sem-desc">Días ≥ 90 <b>O</b> N° LM ≥ 5<br>
    Ausentismo frecuente o prolongado. Ingreso al programa
    de acompañamiento DAP.</div>
  </div>
</div>
<div class="sem-card" style="background:#C00000;">
  <div class="sem-icon">🔴</div>
  <div>
    <div class="sem-title">ROJO — Intervención</div>
    <div class="sem-desc">Días ≥ 180 <b>O</b> N° LM ≥ 10<br>
    Ausentismo crónico. Derivación a COMPIN, evaluación
    médica y posible medida administrativa.</div>
  </div>
</div>
""", unsafe_allow_html=True)

st.divider()

# ── Páginas disponibles ───────────────────────────────────────────────────
st.markdown("### 📋 Páginas disponibles")
st.markdown("""
| Página | Descripción |
|---|---|
| 📊 **Dashboard** | KPIs globales, semáforo, tendencia mensual del ÍA |
| 🏥 **Por CESFAM** | Análisis granular por establecimiento con comparativo |
| 👤 **Por Funcionario** | Búsqueda individual, ranking y clasificación semáforo |
| 📋 **Gestión de Casos** | Estado del programa de acompañamiento y COMPIN |
| 📄 **Reportes** | Generar informe Word y HTML con filtros personalizados |
| 📥 **Cargar Datos** | Carga incremental de archivos Excel (dotación + LM) |
| 📊 **Comparativo** | ÍA por centro, planta, edad, género y día de semana |
""")
