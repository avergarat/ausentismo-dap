"""
metrics.py — Cálculo de indicadores granulares de ausentismo DAP-SSMC
Todos los cálculos sobre Licencias Médicas (LM) con join por RUT.
"""
import pandas as pd
import numpy as np
from modules.db import get_licencias, get_dotacion, get_gestion_casos

# ────────────────────────────────────────────────────────────────────────────
# Colores institucionales para gráficos (por tipo de LM)
# ────────────────────────────────────────────────────────────────────────────
COLORES_TIPO_LM = {
    'L.M. ENFERMEDAD':                             '#8B0000',
    'L.M. ENFERMEDAD PROFESIONAL':                 '#009688',
    'L.M. MATERNAL':                               '#F48FB1',
    'L.M. ENFERMEDAD GRAVE HIJO MENOR DE UN AÑO':  '#FF8A65',
    'L.M. ACCIDENTE EN TRAYECTORIA AL TRABAJO':    '#1565C0',
    'L.M. ACCIDENTE EN LUGAR DE TRABAJO':          '#42A5F5',
    'L.M. PATOLOGIA DEL EMBARAZO':                 '#FFF9C4',
    'L.M. PRORROGA DE MEDICINA PREVENTIVA':        '#F8BBD0',
    'PERMISO SANNA':                               '#FFC107',
}

SEMAFORO_COLORES = {
    'VERDE':   '#1E8B4C',
    'AMARILLO':'#FFC000',
    'NARANJA': '#FF6600',
    'ROJO':    '#C00000',
    'CRITICO': '#6A0DAD',
}

META_IA = {
    'I_CORTE':   6.50,
    'II_CORTE':  13.00,
    'III_CORTE': 19.51,
    'IV_CORTE':  26.02,
    'MENSUAL':    2.17,
}

DOTACION_PROMEDIO = 1602  # dotación de referencia 2026

# ────────────────────────────────────────────────────────────────────────────
# Preparación del DataFrame base
# ────────────────────────────────────────────────────────────────────────────
def build_df(**filtros) -> pd.DataFrame:
    """
    Construye el DataFrame principal de análisis aplicando filtros.
    Enriquece con columnas calculadas (año, mes, semana, tramo etario, etc.)
    """
    df = get_licencias(**filtros)
    if df.empty:
        return df

    # Parseo de fechas
    df['fecha_inicio'] = pd.to_datetime(df['fecha_inicio'], errors='coerce')
    df['fecha_termino'] = pd.to_datetime(df['fecha_termino'], errors='coerce')
    df['d_fecha_nac']  = pd.to_datetime(df['d_fecha_nac'], errors='coerce')

    # Columnas temporales
    df['anio']     = df['fecha_inicio'].dt.year
    df['mes']      = df['fecha_inicio'].dt.month
    df['mes_nom']  = df['fecha_inicio'].dt.strftime('%b %Y')
    df['mes_key']  = df['fecha_inicio'].dt.to_period('M').astype(str)
    df['semana']   = df['fecha_inicio'].dt.isocalendar().week.astype(int)
    df['dia_semana'] = df['fecha_inicio'].dt.day_name()
    df['trimestre'] = df['fecha_inicio'].dt.quarter

    # Edad calculada al momento de inicio de LM
    df['edad_calc'] = (
        (df['fecha_inicio'] - df['d_fecha_nac']).dt.days / 365.25
    ).round(1)
    edad = df['edad_calc'].fillna(df.get('edad_anos', pd.Series(dtype=float)))
    df['tramo_etario'] = pd.cut(
        edad,
        bins=[0, 32, 52, 200],
        labels=['18-32 años', '33-52 años', '53+ años'],
        right=True
    ).astype(str).replace('nan', 'Sin datos')

    # Columnas numéricas
    df['dias_periodo'] = pd.to_numeric(df['dias_periodo'], errors='coerce').fillna(0)
    df['costo']        = pd.to_numeric(df['costo'], errors='coerce').fillna(0)
    df['total_dias']   = pd.to_numeric(df['total_dias'], errors='coerce').fillna(0)

    # Clasificación de duración
    bins_dur  = [0, 3, 7, 15, 30, 90, 180, 9999]
    labs_dur  = ['1-3d', '4-7d', '8-15d', '16-30d', '31-90d', '91-180d', '>180d']
    df['rango_duracion'] = pd.cut(df['dias_periodo'], bins=bins_dur, labels=labs_dur).astype(str)

    # Limpieza de campos de texto
    for c in ['nombre_unidad', 'planta', 'genero', 'calidad_juridica', 'tipo_lm']:
        df[c] = df[c].str.strip().str.upper().fillna('SIN DATOS')

    return df


# ────────────────────────────────────────────────────────────────────────────
# Indicadores Clave — nivel global
# ────────────────────────────────────────────────────────────────────────────
def kpis_globales(df: pd.DataFrame, dotacion_prom: float = DOTACION_PROMEDIO) -> dict:
    if df.empty:
        return {}

    n_lm       = len(df)
    dias_total = df['dias_periodo'].sum()
    costo_total = df['costo'].sum()
    n_func     = df['rut'].nunique()
    n_meses    = max(df['mes_key'].nunique(), 1)
    dot_total  = dotacion_prom * n_meses

    ia_acum  = dias_total / dotacion_prom if dotacion_prom > 0 else 0
    ia_mensual = ia_acum / n_meses if n_meses > 0 else 0
    tf       = n_lm / dot_total * 100 if dot_total > 0 else 0    # TF x 100 func
    tg       = dias_total / n_lm if n_lm > 0 else 0
    pct_corto  = len(df[df['dias_periodo'] <= 15]) / n_lm * 100 if n_lm > 0 else 0
    pct_prolong = len(df[df['dias_periodo'] >= 180]) / n_lm * 100 if n_lm > 0 else 0
    pct_muy_corto = len(df[df['dias_periodo'] <= 3]) / n_lm * 100 if n_lm > 0 else 0
    costo_dia  = costo_total / dias_total if dias_total > 0 else 0

    return {
        'n_lm':          n_lm,
        'dias_total':    int(dias_total),
        'costo_total':   costo_total,
        'n_func':        n_func,
        'n_meses':       n_meses,
        'ia_acumulado':  round(ia_acum, 2),
        'ia_mensual':    round(ia_mensual, 2),
        'tasa_frecuencia': round(tf, 2),
        'tasa_gravedad': round(tg, 2),
        'pct_corto':     round(pct_corto, 1),
        'pct_prolongado': round(pct_prolong, 1),
        'pct_muy_corto': round(pct_muy_corto, 1),
        'costo_por_dia': round(costo_dia, 0),
        'lm_por_func':   round(n_lm / n_func, 1) if n_func > 0 else 0,
        'dias_por_func': round(dias_total / n_func, 1) if n_func > 0 else 0,
    }


# ────────────────────────────────────────────────────────────────────────────
# Índice de Ausentismo mensual (serie temporal)
# ────────────────────────────────────────────────────────────────────────────
def ia_serie_mensual(df: pd.DataFrame, dotacion_prom: float = DOTACION_PROMEDIO) -> pd.DataFrame:
    """Retorna IA mensual con metas para graficar tendencia."""
    if df.empty:
        return pd.DataFrame()

    agg = (df.groupby(['mes_key', 'anio', 'mes'], as_index=False)
             .agg(dias=('dias_periodo', 'sum'),
                  n_lm=('rut', 'count'),
                  costo=('costo', 'sum'),
                  n_func=('rut', 'nunique'))
             .sort_values(['anio', 'mes']))

    agg['ia_mensual']   = (agg['dias'] / dotacion_prom).round(3)
    agg['ia_acumulado'] = agg['ia_mensual'].cumsum().round(3)
    agg['meta_mensual'] = META_IA['MENSUAL']
    agg['tg']           = (agg['dias'] / agg['n_lm']).round(2)
    agg['semaforo']     = agg['ia_mensual'].apply(semaforo_cesfam)
    return agg


# ────────────────────────────────────────────────────────────────────────────
# KPIs por CESFAM / Unidad
# ────────────────────────────────────────────────────────────────────────────
def kpis_por_cesfam(df: pd.DataFrame, dotacion_prom: float = DOTACION_PROMEDIO) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    # Dotación por unidad (desde dotacion table)
    df_dot = get_dotacion()
    dot_x_unidad = {}
    if not df_dot.empty:
        dot_x_unidad = (df_dot.groupby('unidad')['rut']
                         .count().to_dict())

    n_meses = max(df['mes_key'].nunique(), 1)

    def _agg(grp):
        n_lm    = len(grp)
        dias    = grp['dias_periodo'].sum()
        costo   = grp['costo'].sum()
        n_func  = grp['rut'].nunique()
        unidad  = grp['nombre_unidad'].iloc[0]
        dot     = dot_x_unidad.get(unidad, dotacion_prom / 11)  # ~prom por CESFAM
        ia      = dias / dot if dot > 0 else 0
        tg      = dias / n_lm if n_lm > 0 else 0
        tf      = n_lm / (dot * n_meses) * 100 if dot > 0 else 0
        pct_c   = len(grp[grp['dias_periodo'] <= 15]) / n_lm * 100 if n_lm > 0 else 0
        pct_p   = len(grp[grp['dias_periodo'] >= 180]) / n_lm * 100 if n_lm > 0 else 0
        pct_mc  = len(grp[grp['dias_periodo'] <= 3]) / n_lm * 100 if n_lm > 0 else 0
        rec5    = grp.groupby('rut').size()
        n_rec   = (rec5 >= 5).sum()
        return pd.Series({
            'n_lm': n_lm, 'dias_total': int(dias), 'costo_total': costo,
            'n_funcionarios': n_func, 'dotacion_ref': dot,
            'ia_acumulado': round(ia, 2),
            'ia_mensual': round(ia / n_meses, 3),
            'tasa_frecuencia': round(tf, 2),
            'tasa_gravedad': round(tg, 2),
            'pct_corto': round(pct_c, 1),
            'pct_prolongado': round(pct_p, 1),
            'pct_muy_corto': round(pct_mc, 1),
            'n_recurrentes_5': int(n_rec),
            'costo_por_dia': round(costo / dias, 0) if dias > 0 else 0,
            'lm_por_func': round(n_lm / n_func, 1) if n_func > 0 else 0,
        })

    result = (df.groupby('nombre_unidad', group_keys=False)
                .apply(_agg)
                .reset_index()
                .rename(columns={'nombre_unidad': 'cesfam'}))
    result['semaforo'] = result['ia_mensual'].apply(semaforo_cesfam)
    result = result.sort_values('ia_acumulado', ascending=False)
    return result


# ────────────────────────────────────────────────────────────────────────────
# KPIs por Estamento / Planta
# ────────────────────────────────────────────────────────────────────────────
def kpis_por_planta(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    n_meses = max(df['mes_key'].nunique(), 1)

    def _agg(grp):
        n_lm  = len(grp)
        dias  = grp['dias_periodo'].sum()
        costo = grp['costo'].sum()
        n_func = grp['rut'].nunique()
        return pd.Series({
            'n_lm': n_lm, 'dias_total': int(dias), 'costo_total': costo,
            'n_funcionarios': n_func,
            'tasa_gravedad': round(dias/n_lm, 2) if n_lm > 0 else 0,
            'pct_del_total': 0,  # se calcula abajo
            'lm_por_func': round(n_lm/n_func, 1) if n_func > 0 else 0,
            'dias_por_func': round(dias/n_func, 1) if n_func > 0 else 0,
        })

    result = df.groupby('planta').apply(_agg).reset_index()
    total_dias = result['dias_total'].sum()
    result['pct_del_total'] = (result['dias_total'] / total_dias * 100).round(1)
    return result.sort_values('dias_total', ascending=False)


# ────────────────────────────────────────────────────────────────────────────
# KPIs por Funcionario individual (join con dotación por RUT)
# ────────────────────────────────────────────────────────────────────────────
def kpis_por_funcionario(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    def _agg(grp):
        n_lm      = len(grp)
        dias      = grp['dias_periodo'].sum()
        costo     = grp['costo'].sum()
        ult_tipo  = grp.sort_values('fecha_inicio')['tipo_lm'].iloc[-1] if n_lm > 0 else ''
        ult_fecha = grp['fecha_inicio'].max()
        n_anio    = grp[grp['anio'] == grp['anio'].max()]['rut'].count()
        return pd.Series({
            'nombre':       grp['nombre'].iloc[0],
            'unidad':       grp['nombre_unidad'].iloc[0],
            'planta':       grp['planta'].iloc[0],
            'genero':       grp['genero'].iloc[0],
            'calidad':      grp['calidad_juridica'].iloc[0],
            'n_lm_total':   n_lm,
            'dias_total':   int(dias),
            'costo_total':  round(costo, 0),
            'tg':           round(dias/n_lm, 1) if n_lm > 0 else 0,
            'ult_tipo_lm':  ult_tipo,
            'ult_fecha_lm': ult_fecha,
            'n_lm_ult_anio': int(n_anio),
        })

    result = df.groupby('rut').apply(_agg).reset_index()
    result['semaforo']   = result.apply(
        lambda r: semaforo_funcionario(r['dias_total'], r['n_lm_total']), axis=1)
    result['prioridad']  = result['semaforo'].map(
        {'CRITICO': 0, 'ROJO': 1, 'NARANJA': 2, 'AMARILLO': 3, 'VERDE': 4})
    result = result.sort_values(['prioridad', 'dias_total'], ascending=[True, False])

    # Enriquecer con datos de gestión
    df_gest = get_gestion_casos()
    if not df_gest.empty:
        result = result.merge(
            df_gest[['rut', 'proceso', 'vigente', 'responsable', 'compin']],
            on='rut', how='left'
        )
    return result


# ────────────────────────────────────────────────────────────────────────────
# Análisis de recurrencia
# ────────────────────────────────────────────────────────────────────────────
def analisis_recurrencia(df: pd.DataFrame) -> pd.DataFrame:
    """Ranking de funcionarios por número de LM (identificar ausentismo habitual)."""
    if df.empty:
        return pd.DataFrame()
    cnt = df.groupby('rut').size().rename('n_lm').reset_index()
    cnt['nivel'] = pd.cut(cnt['n_lm'],
                          bins=[0, 2, 4, 9, 19, 9999],
                          labels=['1-2 LM', '3-4 LM', '5-9 LM', '10-19 LM', '≥20 LM'])
    return cnt.merge(
        df.groupby('rut').agg(
            nombre=('nombre', 'first'),
            unidad=('nombre_unidad', 'first'),
            planta=('planta', 'first'),
            dias_total=('dias_periodo', 'sum'),
            costo_total=('costo', 'sum')
        ).reset_index(), on='rut'
    ).sort_values('n_lm', ascending=False)


# ────────────────────────────────────────────────────────────────────────────
# Distribución por tipo de LM (para gráfico de torta/barras)
# ────────────────────────────────────────────────────────────────────────────
def dist_tipo_lm(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    agg = (df.groupby('tipo_lm')
             .agg(n_lm=('rut', 'count'),
                  dias=('dias_periodo', 'sum'),
                  costo=('costo', 'sum'))
             .reset_index()
             .sort_values('n_lm', ascending=False))
    agg['pct_lm']   = (agg['n_lm'] / agg['n_lm'].sum() * 100).round(1)
    agg['pct_dias'] = (agg['dias'] / agg['dias'].sum() * 100).round(1)
    agg['color']    = agg['tipo_lm'].map(COLORES_TIPO_LM).fillna('#AAAAAA')
    return agg


# ────────────────────────────────────────────────────────────────────────────
# Distribución por duración (histograma)
# ────────────────────────────────────────────────────────────────────────────
def dist_duracion(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    orden = ['1-3d', '4-7d', '8-15d', '16-30d', '31-90d', '91-180d', '>180d']
    agg = (df.groupby('rango_duracion')
             .agg(n_lm=('rut', 'count'), dias=('dias_periodo', 'sum'))
             .reindex(orden).fillna(0).reset_index())
    agg['pct'] = (agg['n_lm'] / agg['n_lm'].sum() * 100).round(1)
    return agg


# ────────────────────────────────────────────────────────────────────────────
# Distribución por día de inicio (patrón lunes)
# ────────────────────────────────────────────────────────────────────────────
def dist_dia_semana(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    orden = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    nombres = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    agg = (df.groupby('dia_semana')
             .agg(n_lm=('rut', 'count'))
             .reindex(orden).fillna(0).reset_index())
    agg['dia_es'] = nombres
    agg['pct']    = (agg['n_lm'] / agg['n_lm'].sum() * 100).round(1)
    return agg


# ────────────────────────────────────────────────────────────────────────────
# Comparativo por corte (I, II, III, IV)
# ────────────────────────────────────────────────────────────────────────────
def comparativo_cortes(df: pd.DataFrame, anio: int,
                        dotacion_prom: float = DOTACION_PROMEDIO) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    df_anio = df[df['anio'] == anio].copy()
    resultados = []
    cortes = [
        ('I Corte',   [1,2,3],       META_IA['I_CORTE']),
        ('II Corte',  [1,2,3,4,5,6], META_IA['II_CORTE']),
        ('III Corte', list(range(1,10)), META_IA['III_CORTE']),
        ('IV Corte',  list(range(1,13)), META_IA['IV_CORTE']),
    ]
    for nombre, meses, meta in cortes:
        sub = df_anio[df_anio['mes'].isin(meses)]
        dias = sub['dias_periodo'].sum()
        n_meses = len(set(sub['mes_key'].tolist()))
        ia = dias / dotacion_prom if dotacion_prom > 0 else 0
        delta = ia - meta
        resultados.append({
            'corte': nombre, 'meses': len(meses),
            'dias': int(dias), 'n_lm': len(sub),
            'ia_acumulado': round(ia, 2),
            'meta': meta,
            'delta': round(delta, 2),
            'cumple': '✅' if delta <= 0 else '⚠️' if delta <= 0.5 else '🔴',
        })
    return pd.DataFrame(resultados)


# ────────────────────────────────────────────────────────────────────────────
# Semáforos
# ────────────────────────────────────────────────────────────────────────────
def semaforo_funcionario(dias_acum: float, n_lm: int) -> str:
    if dias_acum >= 180 or n_lm >= 10:
        return 'ROJO'
    if dias_acum >= 90 or n_lm >= 5:
        return 'NARANJA'
    if dias_acum >= 30 or n_lm >= 3:
        return 'AMARILLO'
    return 'VERDE'

def semaforo_cesfam(ia_mensual: float) -> str:
    if ia_mensual > 2.60:
        return 'ROJO'
    if ia_mensual > 2.17:
        return 'AMARILLO'
    return 'VERDE'

def emoji_semaforo(nivel: str) -> str:
    return {'VERDE': '🟢', 'AMARILLO': '🟡', 'NARANJA': '🟠',
            'ROJO': '🔴', 'CRITICO': '🟣'}.get(nivel, '⚪')

def color_semaforo(nivel: str) -> str:
    return SEMAFORO_COLORES.get(nivel, '#AAAAAA')


# ────────────────────────────────────────────────────────────────────────────
# Mapa de corte según fecha
# ────────────────────────────────────────────────────────────────────────────
def get_corte(mes: int) -> str:
    if mes <= 3:   return 'I Corte'
    if mes <= 6:   return 'II Corte'
    if mes <= 9:   return 'III Corte'
    return 'IV Corte'


# ────────────────────────────────────────────────────────────────────────────
# Resumen completo para reportes
# ────────────────────────────────────────────────────────────────────────────
def resumen_completo(**filtros) -> dict:
    df = build_df(**filtros)
    return {
        'df':              df,
        'globales':        kpis_globales(df),
        'serie_mensual':   ia_serie_mensual(df),
        'por_cesfam':      kpis_por_cesfam(df),
        'por_planta':      kpis_por_planta(df),
        'por_funcionario': kpis_por_funcionario(df),
        'tipo_lm':         dist_tipo_lm(df),
        'duracion':        dist_duracion(df),
        'dia_semana':      dist_dia_semana(df),
        'recurrencia':     analisis_recurrencia(df),
    }
