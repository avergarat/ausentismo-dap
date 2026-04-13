"""
Carga incremental de archivos Excel — dotación y licencias médicas
"""
import streamlit as st
from modules.sidebar_css import inject as _inject_css
import pandas as pd
from modules.db import get_cargas_log, get_stats, init_db
from modules.loader import smart_load
from modules.ui import show_table

st.set_page_config(page_title="Cargar Datos | Ausentismo", page_icon="📥", layout="wide")
init_db()
_inject_css()

st.title("📥 Carga de Datos")
st.caption("Carga incremental: solo se insertan registros nuevos, los duplicados se omiten automáticamente.")
st.divider()

# ── Estado actual de la base ──────────────────────────────────────────────
stats = get_stats()
col1,col2,col3,col4 = st.columns(4)
col1.metric("LM en base", f"{stats['n_licencias']:,}")
col2.metric("Dotación", f"{stats['n_dotacion']:,}")
col3.metric("Casos gestión", f"{stats['n_gestion']:,}")
col4.metric("Cargas realizadas", stats['n_cargas'])
if stats['periodo_ini']:
    st.info(f"📅 Período actual: **{stats['periodo_ini']}** → **{stats['periodo_fin']}**")

st.divider()

# ── Uploader ──────────────────────────────────────────────────────────────
st.subheader("📂 Cargar archivo Excel")

st.markdown("""
**Archivos aceptados:**
- `Dotación_03_2023.xlsx` — contiene dotación del personal (hojas: SIN DUPLICADOS, DUPLICADOS (2))
- `BASE AUSENTISMO 2026 [...].xlsx` — contiene licencias médicas (hoja: 31.03.2026) y gestión de casos (hoja: AUSENTISMO)
- Cualquier actualización posterior de los mismos archivos con datos nuevos

La carga es **incremental**: los registros ya existentes (misma clave) no se duplican.
""")

uploaded_files = st.file_uploader(
    "Arrastra aquí los archivos Excel",
    type=['xlsx', 'xls'],
    accept_multiple_files=True,
    help="Puedes cargar uno o varios archivos a la vez"
)

if uploaded_files:
    if st.button("🚀 Iniciar carga", type="primary"):
        for uploaded_file in uploaded_files:
            st.markdown(f"---\n**Procesando:** `{uploaded_file.name}`")
            progress_bar = st.progress(0)
            status_text  = st.empty()

            # Guardar temporalmente
            import tempfile, os
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name

            try:
                def cb(pct, msg):
                    progress_bar.progress(pct)
                    status_text.text(msg)

                results = smart_load(tmp_path, progress_cb=cb)

                for r in results:
                    hoja = r.get('hoja', '?')
                    if 'insertados' in r and 'actualizados' in r:
                        # Dotación o gestión
                        st.success(
                            f"✅ **{hoja}** — "
                            f"{r['insertados']} nuevos, "
                            f"{r['actualizados']} actualizados, "
                            f"{r['total']} total"
                        )
                    elif 'insertados' in r and 'omitidos' in r:
                        # Licencias
                        st.success(
                            f"✅ **{hoja}** — "
                            f"{r['insertados']} nuevas LM insertadas, "
                            f"{r['omitidos']} duplicadas omitidas | "
                            f"Período: {r.get('periodo','')}"
                        )

                progress_bar.progress(1.0)
                status_text.text("✅ Completado")

            except Exception as e:
                st.error(f"❌ Error al procesar `{uploaded_file.name}`: {e}")
                st.exception(e)
            finally:
                os.unlink(tmp_path)

        # Refrescar stats
        st.cache_data.clear()
        st.rerun()

# ── Instrucciones detalladas ──────────────────────────────────────────────
with st.expander("📖 Instrucciones de carga detalladas"):
    st.markdown("""
    ### Flujo de carga recomendado

    **Paso 1 — Dotación** (una vez o cuando se actualice la plantilla):
    - Carga `Dotación_03_2023.xlsx` o el archivo de dotación más reciente
    - Se leen las hojas `SIN DUPLICADOS` y `DUPLICADOS (2)`
    - Clave: RUT (upsert — actualiza si ya existe)

    **Paso 2 — Base de ausentismo** (en cada actualización):
    - Carga `BASE AUSENTISMO 2026 [...].xlsx` o versión actualizada
    - Se leen la hoja transaccional de LM (ej. `31.03.2026`) y la hoja `AUSENTISMO`
    - Clave LM: RUT + Fecha inicio + Fecha término + Tipo LM (no duplica)
    - Los registros CGR excluidos NO se insertan

    **Actualización incremental:**
    - Puedes cargar el mismo archivo actualizado — solo se insertarán las LM nuevas
    - Los registros existentes no se modifican ni duplican
    - El período se extiende automáticamente

    ### Archivos esperados
    | Archivo | Hojas leídas | Contenido |
    |---|---|---|
    | Dotación_03_2023.xlsx | SIN DUPLICADOS, DUPLICADOS (2) | Datos personales y contractuales |
    | BASE AUSENTISMO 2026.xlsx | 31.03.2026 (o similar), AUSENTISMO | LM y gestión de casos |
    """)

# ── Historial de cargas ───────────────────────────────────────────────────
st.divider()
st.subheader("📜 Historial de Cargas")
cargas = get_cargas_log()
if cargas.empty:
    st.info("Aún no se han realizado cargas.")
else:
    show_table(
        cargas[['id','archivo','hoja','tipo','registros_nuevos',
                'registros_actualizados','periodo_ini','periodo_fin',
                'fecha_carga','notas']].rename(columns={
            'id':'ID','archivo':'Archivo','hoja':'Hoja','tipo':'Tipo',
            'registros_nuevos':'Nuevos','registros_actualizados':'Actualizados',
            'periodo_ini':'Período Ini','periodo_fin':'Período Fin',
            'fecha_carga':'Fecha Carga','notas':'Notas'
        })
    )

# ── Zona de riesgo ────────────────────────────────────────────────────────
with st.expander("⚠️ Administración de datos (zona de riesgo)"):
    st.warning("Las siguientes operaciones son IRREVERSIBLES. Usa con precaución.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Limpiar SOLO licencias", use_container_width=True):
            confirm = st.text_input("Escribe CONFIRMAR para borrar todas las LM:")
            if confirm == "CONFIRMAR":
                from modules.db import execute
                execute("DELETE FROM licencias")
                execute("DELETE FROM cargas_log WHERE tipo='licencias'")
                st.cache_data.clear()
                st.success("Licencias eliminadas.")
                st.rerun()
    with col2:
        if st.button("🗑️ Resetear base completa", use_container_width=True):
            confirm2 = st.text_input("Escribe RESET COMPLETO para confirmar:")
            if confirm2 == "RESET COMPLETO":
                from modules.db import execute
                for tabla in ['licencias','dotacion','gestion_casos','cargas_log']:
                    execute(f"DELETE FROM {tabla}")
                st.cache_data.clear()
                st.success("Base de datos reseteada.")
                st.rerun()
