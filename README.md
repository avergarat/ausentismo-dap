# Sistema de Seguimiento del Ausentismo Laboral — DAP-SSMC

**Dirección de Atención Primaria · Servicio de Salud Metropolitano Central**

Aplicación Streamlit para el seguimiento, análisis y gestión del ausentismo por Licencias Médicas (LM).

## Características

- Carga incremental de archivos Excel (dotación + base LM)
- Join automático por **RUT** entre dotación y licencias
- Exclusión automática de items CGR (feriados, compensatorios, teletrabajo, etc.)
- 6 páginas interactivas con filtros dinámicos
- Generación de informes Word y HTML
- Semáforo por CESFAM y por funcionario
- Indicadores: ÍA, TF, TG, % corta, % prolongada, costo

## Páginas

| Página | Descripción |
|---|---|
| 📊 Dashboard | KPIs globales, tendencia ÍA, semáforo |
| 🏥 Por CESFAM | Análisis granular por establecimiento |
| 👤 Por Funcionario | Ranking, búsqueda y ficha individual |
| 📋 Gestión Casos | Estado del programa de acompañamiento |
| 📄 Reportes | Generar Word y HTML |
| 📥 Cargar Datos | Carga incremental de Excel |

## Instalación

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Fuentes de datos

1. `Dotación_03_2023.xlsx` — Hojas: `SIN DUPLICADOS`, `DUPLICADOS (2)`
2. `BASE AUSENTISMO 2026 [...].xlsx` — Hojas: `31.03.2026`, `AUSENTISMO`

**Clave de join:** RUT

## Exclusiones CGR aplicadas automáticamente

- Feriados Legales
- Días Compensatorios
- Permiso Descanso Reparatorio
- Permiso entre Feriados
- Comisión de Servicio
- Teletrabajo Funciones Habituales
- Teletrabajo Funciones No Habituales
