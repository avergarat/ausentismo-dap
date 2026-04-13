"""
sidebar_css.py — CSS del menú lateral azul institucional DAP-SSMC.
Importar e invocar inject() al inicio de cada página.
"""
import streamlit as st

_SIDEBAR_CSS = """
<style>
/* ── Fondo sidebar ─────────────────────────────────────── */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div:first-child {
    background: #00386B !important;
}

/* ── TODO el texto blanco ──────────────────────────────── */
[data-testid="stSidebar"] *,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div,
[data-testid="stSidebar"] a,
[data-testid="stSidebar"] small,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4,
[data-testid="stSidebar"] li,
[data-testid="stSidebar"] svg {
    color: white !important;
    fill: white !important;
}

/* ── Navegación lateral ────────────────────────────────── */
[data-testid="stSidebar"] [data-testid="stSidebarNavItems"] a {
    color: white !important;
    font-weight: 500;
    border-radius: 6px;
}
[data-testid="stSidebar"] [data-testid="stSidebarNavItems"] a:hover {
    background: rgba(255,255,255,0.15) !important;
}
[data-testid="stSidebar"] [data-testid="stSidebarNavItems"] a[aria-current="page"] {
    background: rgba(255,255,255,0.25) !important;
    font-weight: 700;
}

/* ── Separador ─────────────────────────────────────────── */
[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.3) !important;
}

/* ── Inputs de texto y número ──────────────────────────── */
[data-testid="stSidebar"] input {
    background: rgba(255,255,255,0.12) !important;
    color: white !important;
    border-color: rgba(255,255,255,0.4) !important;
    caret-color: white !important;
}
[data-testid="stSidebar"] input::placeholder {
    color: rgba(255,255,255,0.6) !important;
}

/* ── Selectbox y Multiselect — contenedor ──────────────── */
[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div,
[data-testid="stSidebar"] .stMultiSelect [data-baseweb="select"] > div {
    background: rgba(255,255,255,0.12) !important;
    border-color: rgba(255,255,255,0.4) !important;
}

/* ── Texto dentro del select ───────────────────────────── */
[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] span,
[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] div,
[data-testid="stSidebar"] .stMultiSelect [data-baseweb="select"] span,
[data-testid="stSidebar"] .stMultiSelect [data-baseweb="select"] div {
    color: white !important;
    background: transparent !important;
}

/* ── Chips/tags del multiselect ────────────────────────── */
[data-testid="stSidebar"] [data-baseweb="tag"] {
    background: rgba(255,255,255,0.25) !important;
    color: white !important;
}
[data-testid="stSidebar"] [data-baseweb="tag"] span,
[data-testid="stSidebar"] [data-baseweb="tag"] svg {
    color: white !important;
    fill: white !important;
}

/* ── Flecha del select ─────────────────────────────────── */
[data-testid="stSidebar"] [data-baseweb="select"] svg {
    fill: white !important;
    color: white !important;
}

/* ── Placeholder del select ────────────────────────────── */
[data-testid="stSidebar"] [data-baseweb="select"] [class*="placeholder"] {
    color: rgba(255,255,255,0.7) !important;
}

/* ── Títulos principales (fuera del sidebar) ───────────── */
h1, h2, h3 { color: #00386B; }
</style>
"""

def inject():
    """Inyecta CSS del sidebar azul. Llamar al inicio de cada página."""
    st.markdown(_SIDEBAR_CSS, unsafe_allow_html=True)
