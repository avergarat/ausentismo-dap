"""
Generación de informes Word y HTML con filtros personalizados
"""
import streamlit as st
import io
from datetime import datetime
from modules.db import get_catalogo, get_periodo, init_db
from modules.metrics import resumen_completo
from modules.reports import generar_word, generar_html

st.set_page_config(page_title="Reportes | Ausentismo", page_icon="📄", layout="wide")
init_db()

st.title("📄 Generación de Informes")
st.caption("Genera informes Word y HTML con los filtros y período que necesites.")
st.divider()

# ── Filtros ───────────────────────────────────────────────────────────────
with st.expander("⚙️ Configurar filtros del informe", expanded=True):
    unidades  = get_catalogo('licencias', 'nombre_unidad')
    plantas   = get_catalogo('licencias', 'planta')
    periodo   = get_periodo()

    col1, col2 = st.columns(2)
    with col1:
        sel_u   = st.multiselect("Establecimientos", unidades, placeholder="Todos")
        sel_p   = st.multiselect("Planta / Estamento", plantas, placeholder="Todos")
        fi      = st.text_input("Período desde (YYYY-MM-DD)", value=periodo[0] or '')
        ff      = st.text_input("Período hasta (YYYY-MM-DD)", value=periodo[1] or '')
    with col2:
        dot     = st.number_input("Dotación promedio", value=1602, step=10)
        titulo_extra = st.text_input("Descripción del período", value="I Corte 2026 (Enero–Marzo)")
        incluir_func = st.checkbox("Incluir tabla de funcionarios (datos sensibles)", value=False)
        top_n   = st.number_input("Top N funcionarios en el informe", value=30, step=5)

# ── Botones generación ────────────────────────────────────────────────────
st.divider()
col_word, col_html = st.columns(2)

def _generar_resumen():
    return resumen_completo(
        unidades=sel_u or None,
        plantas=sel_p or None,
        fecha_ini=fi or None,
        fecha_fin=ff or None,
        excluir_cgr=True
    )

with col_word:
    st.markdown("### 📝 Informe Word (.docx)")
    st.markdown("""
    Informe completo en formato Word con:
    - Portada institucional
    - Resumen ejecutivo con KPIs
    - Tablas por CESFAM, planta y tipo de LM
    - Evolución mensual del ÍA
    - Recomendaciones automáticas
    - Listado de funcionarios prioritarios
    """)
    if st.button("🚀 Generar Word", type="primary", use_container_width=True):
        with st.spinner("Generando informe Word..."):
            try:
                resumen = _generar_resumen()
                if resumen['df'].empty:
                    st.warning("Sin datos para los filtros seleccionados.")
                else:
                    word_bytes = generar_word(resumen, titulo_extra, dot)
                    fecha_str = datetime.now().strftime('%Y%m%d_%H%M')
                    st.download_button(
                        label="⬇️ Descargar Informe Word",
                        data=word_bytes,
                        file_name=f"Informe_Ausentismo_DAP_SSMC_{fecha_str}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True
                    )
                    st.success(f"✅ Informe generado con {resumen['globales'].get('n_lm',0):,} LM analizadas.")
            except Exception as e:
                st.error(f"Error al generar: {e}")
                st.exception(e)

with col_html:
    st.markdown("### 🌐 Informe HTML")
    st.markdown("""
    Informe web interactivo con:
    - Vista responsive para pantalla e impresión
    - Tablas con colores semáforo
    - KPI cards visuales
    - Exportable como PDF desde el navegador
    """)
    if st.button("🚀 Generar HTML", type="primary", use_container_width=True):
        with st.spinner("Generando informe HTML..."):
            try:
                resumen = _generar_resumen()
                if resumen['df'].empty:
                    st.warning("Sin datos para los filtros seleccionados.")
                else:
                    html_str = generar_html(resumen, titulo_extra)
                    fecha_str = datetime.now().strftime('%Y%m%d_%H%M')
                    st.download_button(
                        label="⬇️ Descargar Informe HTML",
                        data=html_str.encode('utf-8'),
                        file_name=f"Informe_Ausentismo_DAP_SSMC_{fecha_str}.html",
                        mime="text/html",
                        use_container_width=True
                    )
                    st.success("✅ Informe HTML generado. Abre en el navegador y usa Ctrl+P para imprimir/guardar como PDF.")
            except Exception as e:
                st.error(f"Error al generar: {e}")
                st.exception(e)

# ── Vista previa KPIs ─────────────────────────────────────────────────────
st.divider()
st.subheader("👁️ Vista previa de KPIs del período seleccionado")

if st.button("Calcular vista previa"):
    with st.spinner("Calculando..."):
        resumen = _generar_resumen()
        g = resumen.get('globales', {})
        if not g:
            st.warning("Sin datos.")
        else:
            c1,c2,c3,c4,c5,c6 = st.columns(6)
            c1.metric("N° LM", f"{g.get('n_lm',0):,}")
            c2.metric("Días", f"{g.get('dias_total',0):,}")
            c3.metric("ÍA mensual", f"{g.get('ia_mensual',0):.3f}")
            c4.metric("ÍA acumulado", f"{g.get('ia_acumulado',0):.2f}")
            c5.metric("Costo", f"${g.get('costo_total',0)/1e6:.1f}M")
            c6.metric("Funcionarios", f"{g.get('n_func',0):,}")
