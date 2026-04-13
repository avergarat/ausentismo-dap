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


def _fmt_cell(val):
    """
    Formatea un valor individual para mostrar en tabla:
    - int  → separador de miles:  1.234.567
    - float sin decimales → igual que int
    - float con decimales → hasta 2 decimales con separador: 1.234,56
    - strings ya formateados ($ , %, letras) → sin cambios
    """
    if pd.isna(val):
        return '—'
    if isinstance(val, bool):
        return str(val)
    if isinstance(val, int):
        return f"{val:,}"
    if isinstance(val, float):
        if val == int(val):           # sin decimales reales → entero
            return f"{int(val):,}"
        return f"{val:,.2f}"
    return str(val)


def _autoformat(df: pd.DataFrame) -> pd.DataFrame:
    """
    Recorre el DataFrame y aplica _fmt_cell() a todas las columnas
    que sean numéricas (int64 / float64) y no estén ya formateadas
    como strings con $, %, etc.
    """
    out = df.copy()
    for col in out.columns:
        dtype = out[col].dtype
        if pd.api.types.is_integer_dtype(dtype):
            out[col] = out[col].apply(lambda x: f"{int(x):,}" if pd.notna(x) else '—')
        elif pd.api.types.is_float_dtype(dtype):
            out[col] = out[col].apply(
                lambda x: (f"{int(x):,}" if x == int(x) else f"{x:,.2f}") if pd.notna(x) else '—'
            )
        # strings → ya están formateados, no tocar
    return out


def show_table(df: pd.DataFrame, max_rows: int = 500) -> None:
    """
    Renderiza un DataFrame como tabla HTML estilizada.
    Aplica automáticamente separador de miles a todas las columnas numéricas.
    Reemplaza st.dataframe() en toda la aplicación.
    """
    global _css_injected
    if not _css_injected:
        st.markdown(_TABLE_CSS, unsafe_allow_html=True)
        _css_injected = True

    if df.empty:
        st.info("Sin datos para mostrar.")
        return

    display = _autoformat(df.head(max_rows).reset_index(drop=True))
    html = display.to_html(
        index=False,
        border=0,
        classes='dap-table',
        na_rep='—',
    )
    st.markdown(html, unsafe_allow_html=True)
    if len(df) > max_rows:
        st.caption(f"Mostrando {max_rows:,} de {len(df):,} filas.")
