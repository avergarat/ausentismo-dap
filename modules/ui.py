"""
ui.py — Helpers de interfaz que evitan dependencia de pyarrow.
st.dataframe() requiere pyarrow (no instalable en Python 32-bit).
Usar show_table() en su lugar.
"""
import streamlit as st
import pandas as pd


_TABLE_CSS = """
<style>
.dap-table {width:100%; border-collapse:collapse; font-size:0.85rem;}
.dap-table th {
    background:#006FB9; color:white; padding:6px 10px;
    text-align:left; white-space:nowrap;
}
.dap-table td {
    padding:5px 10px; border-bottom:1px solid #dde3ee;
    white-space:nowrap;
}
.dap-table tr:nth-child(even) td {background:#f0f4fa;}
.dap-table tr:hover td {background:#dbeafe;}
</style>
"""
_css_injected = False


def show_table(df: pd.DataFrame, max_rows: int = 500) -> None:
    """
    Renderiza un DataFrame como tabla HTML estilizada, sin usar pyarrow.
    Reemplaza st.dataframe() en toda la aplicación.
    """
    global _css_injected
    if not _css_injected:
        st.markdown(_TABLE_CSS, unsafe_allow_html=True)
        _css_injected = True

    if df.empty:
        st.info("Sin datos para mostrar.")
        return

    display = df.head(max_rows).reset_index(drop=True)
    html = display.to_html(
        index=False,
        border=0,
        classes='dap-table',
        na_rep='—',
    )
    st.markdown(html, unsafe_allow_html=True)
    if len(df) > max_rows:
        st.caption(f"Mostrando {max_rows} de {len(df)} filas.")
