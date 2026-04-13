"""
db.py — Gestión de base de datos SQLite para el Sistema de Ausentismo DAP-SSMC
"""
import sqlite3
import os
import pandas as pd
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "ausentismo.db")

# ────────────────────────────────────────────────────────────────────────────
# Conexión
# ────────────────────────────────────────────────────────────────────────────
@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()

# ────────────────────────────────────────────────────────────────────────────
# Inicialización
# ────────────────────────────────────────────────────────────────────────────
DDL = """
CREATE TABLE IF NOT EXISTS dotacion (
    rut             INTEGER PRIMARY KEY,
    dv              TEXT,
    nombre          TEXT,
    planta          TEXT,
    calidad_juridica TEXT,
    genero          TEXT,
    ley             TEXT,
    horas           INTEGER,
    est_codigo      INTEGER,
    est_nombre      TEXT,
    fecha_nacimiento TEXT,
    cod_unidad      INTEGER,
    unidad          TEXT,
    cargo           TEXT,
    funcion         TEXT,
    titulo          TEXT,
    fecha_ini_contrato TEXT,
    fecha_ter_contrato TEXT,
    direccion       TEXT,
    ciudad          TEXT,
    comuna          TEXT,
    fecha_ingreso_servicio TEXT,
    isapre          TEXT,
    afp             TEXT,
    cargas_familiares INTEGER,
    remuneracion    REAL,
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS licencias (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    rut             INTEGER,
    dv              TEXT,
    nombre          TEXT,
    ley             TEXT,
    edad_anos       INTEGER,
    afp             TEXT,
    salud           TEXT,
    cod_unidad      INTEGER,
    nombre_unidad   TEXT,
    genero          TEXT,
    cargo           TEXT,
    calidad_juridica TEXT,
    planta          TEXT,
    num_resolucion  TEXT,
    fecha_resolucion TEXT,
    fecha_inicio    TEXT,
    fecha_termino   TEXT,
    total_dias      INTEGER,
    dias_periodo    INTEGER,
    costo           REAL,
    tipo_lm         TEXT,
    cod_establecimiento INTEGER,
    nombre_establecimiento TEXT,
    saldo_dias_no_reemplazados INTEGER,
    tipo_contrato   TEXT,
    -- Discriminador: 'LM' = Licencia Médica | 'AUSENTISMO' = otra ausencia válida
    categoria       TEXT DEFAULT 'LM',
    carga_id        INTEGER,
    UNIQUE (rut, fecha_inicio, fecha_termino, tipo_lm),
    FOREIGN KEY (carga_id) REFERENCES cargas_log(id)
);

CREATE TABLE IF NOT EXISTS gestion_casos (
    rut             INTEGER PRIMARY KEY,
    nombre          TEXT,
    vigente         TEXT,
    proceso         TEXT,
    resumen_interno TEXT,
    fecha_usf       TEXT,
    compin          TEXT,
    casos_especiales TEXT,
    diferencial     REAL,
    promedio        REAL,
    aus_ajustado    REAL,
    ult_ausentismo  REAL,
    genero          TEXT,
    fecha_nacimiento TEXT,
    establecimiento TEXT,
    estamento       TEXT,
    responsable     TEXT,
    asignacion      TEXT,
    visita_dom      TEXT,
    fecha_comite    TEXT,
    carta           TEXT,
    n_contacto      TEXT,
    correo          TEXT,
    observaciones   TEXT,
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS cargas_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    archivo         TEXT,
    hoja            TEXT,
    tipo            TEXT,
    registros_nuevos     INTEGER DEFAULT 0,
    registros_actualizados INTEGER DEFAULT 0,
    periodo_ini     TEXT,
    periodo_fin     TEXT,
    fecha_carga     TEXT DEFAULT (datetime('now')),
    notas           TEXT
);

CREATE INDEX IF NOT EXISTS idx_lic_rut   ON licencias(rut);
CREATE INDEX IF NOT EXISTS idx_lic_unidad ON licencias(nombre_unidad);
CREATE INDEX IF NOT EXISTS idx_lic_ini   ON licencias(fecha_inicio);
CREATE INDEX IF NOT EXISTS idx_lic_tipo  ON licencias(tipo_lm);
CREATE INDEX IF NOT EXISTS idx_lic_planta ON licencias(planta);
"""

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_conn() as conn:
        conn.executescript(DDL)
        conn.commit()

# ────────────────────────────────────────────────────────────────────────────
# Queries genéricas
# ────────────────────────────────────────────────────────────────────────────
def query_df(sql: str, params=()) -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(sql, conn, params=params)

def execute(sql: str, params=()):
    with get_conn() as conn:
        conn.execute(sql, params)
        conn.commit()

def executemany(sql: str, data: list):
    with get_conn() as conn:
        conn.executemany(sql, data)
        conn.commit()

# ────────────────────────────────────────────────────────────────────────────
# Dotación
# ────────────────────────────────────────────────────────────────────────────
def get_dotacion(unidad=None, planta=None, calidad=None) -> pd.DataFrame:
    where, params = [], []
    if unidad:
        where.append("unidad = ?"); params.append(unidad)
    if planta:
        where.append("planta = ?"); params.append(planta)
    if calidad:
        where.append("calidad_juridica = ?"); params.append(calidad)
    cond = ("WHERE " + " AND ".join(where)) if where else ""
    return query_df(f"SELECT * FROM dotacion {cond}", params)

def upsert_dotacion(rows: list[dict]) -> tuple[int, int]:
    """Upsert dotacion records. Returns (inserted, updated)."""
    inserted = updated = 0
    with get_conn() as conn:
        for r in rows:
            existing = conn.execute("SELECT rut FROM dotacion WHERE rut=?", (r['rut'],)).fetchone()
            cols = ', '.join(r.keys())
            placeholders = ', '.join(['?'] * len(r))
            vals = list(r.values())
            if existing:
                sets = ', '.join(f"{k}=?" for k in r.keys() if k != 'rut')
                uvals = [v for k, v in r.items() if k != 'rut'] + [r['rut']]
                conn.execute(f"UPDATE dotacion SET {sets}, updated_at=datetime('now') WHERE rut=?", uvals)
                updated += 1
            else:
                conn.execute(f"INSERT OR IGNORE INTO dotacion ({cols}) VALUES ({placeholders})", vals)
                inserted += 1
        conn.commit()
    return inserted, updated

# ────────────────────────────────────────────────────────────────────────────
# Licencias
# ────────────────────────────────────────────────────────────────────────────
TIPOS_EXCLUIDOS = {
    'FERIADO LEGAL', 'DIA COMPENSATORIO', 'DÍAS COMPENSATORIOS',
    'DIAS COMPENSATORIOS', 'PERMISO DESCANSO REPARATORIO',
    'PERMISO ENTRE FERIADOS', 'COMISION DE SERVICIO', 'COMISIÓN DE SERVICIO',
    'TELETRABAJO FUNCIONES HABITUALES', 'TELETRABAJO FUNCIONES NO HABITUALES',
}

def get_licencias(
    unidades=None, plantas=None, generos=None,
    tipos_lm=None, calidades=None,
    fecha_ini=None, fecha_fin=None,
    excluir_cgr=True
) -> pd.DataFrame:
    where, params = [], []

    # Siempre excluir items CGR (nunca son ausentismo válido)
    placeholders = ','.join(['?'] * len(TIPOS_EXCLUIDOS))
    where.append(f"UPPER(TRIM(tipo_lm)) NOT IN ({placeholders})")
    params.extend([t.upper() for t in TIPOS_EXCLUIDOS])

    # Filtro por categoría: 'LM' = solo licencias médicas, None = todo ausentismo válido
    if excluir_cgr:  # reusando flag: True = solo LM, False = todo ausentismo
        where.append("categoria = 'LM'")
        params = params  # ya filtrado

    if unidades:
        placeholders = ','.join(['?'] * len(unidades))
        where.append(f"nombre_unidad IN ({placeholders})")
        params.extend(unidades)
    if plantas:
        placeholders = ','.join(['?'] * len(plantas))
        where.append(f"planta IN ({placeholders})")
        params.extend(plantas)
    if generos:
        placeholders = ','.join(['?'] * len(generos))
        where.append(f"genero IN ({placeholders})")
        params.extend(generos)
    if tipos_lm:
        placeholders = ','.join(['?'] * len(tipos_lm))
        where.append(f"tipo_lm IN ({placeholders})")
        params.extend(tipos_lm)
    if calidades:
        placeholders = ','.join(['?'] * len(calidades))
        where.append(f"calidad_juridica IN ({placeholders})")
        params.extend(calidades)
    if fecha_ini:
        where.append("fecha_inicio >= ?"); params.append(fecha_ini)
    if fecha_fin:
        where.append("fecha_inicio <= ?"); params.append(fecha_fin)

    cond = ("WHERE " + " AND ".join(where)) if where else ""
    sql = f"""
        SELECT l.*, d.fecha_nacimiento AS d_fecha_nac, d.isapre, d.afp,
               d.fecha_ingreso_servicio, d.remuneracion, d.comuna, d.ciudad
        FROM licencias l
        LEFT JOIN dotacion d ON l.rut = d.rut
        {cond}
        ORDER BY l.fecha_inicio DESC
    """
    return query_df(sql, params)

def insert_licencias(rows: list[dict], carga_id: int) -> tuple[int, int]:
    inserted = skipped = 0
    cols = ['rut','dv','nombre','ley','edad_anos','afp','salud','cod_unidad',
            'nombre_unidad','genero','cargo','calidad_juridica','planta',
            'num_resolucion','fecha_resolucion','fecha_inicio','fecha_termino',
            'total_dias','dias_periodo','costo','tipo_lm',
            'cod_establecimiento','nombre_establecimiento',
            'saldo_dias_no_reemplazados','tipo_contrato','carga_id']
    sql = f"""
        INSERT OR IGNORE INTO licencias ({', '.join(cols)})
        VALUES ({', '.join(['?']*len(cols))})
    """
    with get_conn() as conn:
        for r in rows:
            vals = [r.get(c) for c in cols[:-1]] + [carga_id]
            cur = conn.execute(sql, vals)
            if cur.rowcount:
                inserted += 1
            else:
                skipped += 1
        conn.commit()
    return inserted, skipped

# ────────────────────────────────────────────────────────────────────────────
# Gestión de Casos
# ────────────────────────────────────────────────────────────────────────────
def get_gestion_casos(vigente=None, proceso=None) -> pd.DataFrame:
    where, params = [], []
    if vigente:
        where.append("vigente = ?"); params.append(vigente)
    if proceso:
        where.append("proceso = ?"); params.append(proceso)
    cond = ("WHERE " + " AND ".join(where)) if where else ""
    return query_df(f"SELECT * FROM gestion_casos {cond}", params)

def upsert_gestion(rows: list[dict]) -> tuple[int, int]:
    inserted = updated = 0
    with get_conn() as conn:
        for r in rows:
            ex = conn.execute("SELECT rut FROM gestion_casos WHERE rut=?", (r['rut'],)).fetchone()
            cols = ', '.join(r.keys())
            placeholders = ', '.join(['?'] * len(r))
            if ex:
                sets = ', '.join(f"{k}=?" for k in r.keys() if k != 'rut')
                uvals = [v for k, v in r.items() if k != 'rut'] + [r['rut']]
                conn.execute(f"UPDATE gestion_casos SET {sets}, updated_at=datetime('now') WHERE rut=?", uvals)
                updated += 1
            else:
                conn.execute(f"INSERT OR IGNORE INTO gestion_casos ({cols}) VALUES ({placeholders})", list(r.values()))
                inserted += 1
        conn.commit()
    return inserted, updated

# ────────────────────────────────────────────────────────────────────────────
# Cargas Log
# ────────────────────────────────────────────────────────────────────────────
def log_carga(archivo, hoja, tipo, nuevos, actualizados, periodo_ini='', periodo_fin='', notas='') -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO cargas_log (archivo,hoja,tipo,registros_nuevos,registros_actualizados,
               periodo_ini,periodo_fin,notas) VALUES (?,?,?,?,?,?,?,?)""",
            (archivo, hoja, tipo, nuevos, actualizados, periodo_ini, periodo_fin, notas)
        )
        conn.commit()
        return cur.lastrowid

def get_cargas_log() -> pd.DataFrame:
    return query_df("SELECT * FROM cargas_log ORDER BY fecha_carga DESC")

# ────────────────────────────────────────────────────────────────────────────
# Catálogos (para filtros)
# ────────────────────────────────────────────────────────────────────────────
def get_catalogo(tabla: str, campo: str) -> list:
    rows = query_df(f"SELECT DISTINCT {campo} FROM {tabla} WHERE {campo} IS NOT NULL ORDER BY {campo}")
    return rows[campo].tolist() if not rows.empty else []

def get_periodo() -> tuple:
    row = query_df("SELECT MIN(fecha_inicio) as ini, MAX(fecha_inicio) as fin FROM licencias")
    return (row['ini'].iloc[0], row['fin'].iloc[0]) if not row.empty else (None, None)

def get_stats() -> dict:
    with get_conn() as conn:
        stats = {}
        stats['n_dotacion']  = conn.execute("SELECT COUNT(*) FROM dotacion").fetchone()[0]
        stats['n_licencias'] = conn.execute("SELECT COUNT(*) FROM licencias").fetchone()[0]
        stats['n_gestion']   = conn.execute("SELECT COUNT(*) FROM gestion_casos").fetchone()[0]
        stats['n_cargas']    = conn.execute("SELECT COUNT(*) FROM cargas_log").fetchone()[0]
        r = conn.execute("SELECT MIN(fecha_inicio), MAX(fecha_inicio) FROM licencias").fetchone()
        stats['periodo_ini'] = r[0] or ''
        stats['periodo_fin'] = r[1] or ''
    return stats
