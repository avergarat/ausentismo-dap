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


def _fmt_int(x):
    try:
        if pd.isna(x):
            return '—'
        return f"{int(x):,}"
    except Exception:
        return str(x)


def _fmt_float(x):
    try:
        if pd.isna(x):
            return '—'
        f = float(x)
        i = int(f)
        if f == i:
            return f"{i:,}"
        return f"{f:,.2f}"
    except Exception:
        return str(x)


def _autoformat(df: pd.DataFrame) -> pd.DataFrame:
    """
    Recorre el DataFrame y aplica separador de miles a columnas numéricas.
    Ignora strings, fechas, booleanos y cualquier columna que falle.
    """
    out = df.copy()
    for col in out.columns:
        try:
            s = out[col]
            # Si el resultado de out[col] es un DataFrame (cols duplicadas), saltar
            if isinstance(s, pd.DataFrame):
                continue
            dtype = s.dtype
            if pd.api.types.is_bool_dtype(dtype):
                continue
            if pd.api.types.is_datetime64_any_dtype(dtype):
                out[col] = s.astype(str).str[:10].replace('NaT', '—')
                continue
            if pd.api.types.is_integer_dtype(dtype):
                out[col] = s.apply(_fmt_int)
            elif pd.api.types.is_float_dtype(dtype):
                out[col] = s.apply(_fmt_float)
            # object / string: ya formateados, no tocar
        except Exception:
            pass  # columna problemática → dejar sin cambio
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
