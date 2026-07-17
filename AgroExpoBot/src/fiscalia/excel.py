import os
import pandas as pd
from datetime import datetime

try:
    from utils.cedula import normalizar_cedula
    from utils.seguridad import leer_excel_seguro, guardar_excel_seguro
    from utils.config import GUARDAR_CADA
except ImportError:
    from src.utils.cedula import normalizar_cedula
    from src.utils.seguridad import leer_excel_seguro, guardar_excel_seguro
    from src.utils.config import GUARDAR_CADA


# ==============================
# RUTAS
# ==============================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

DATA_DIR = os.path.join(BASE_DIR, "data")

os.makedirs(DATA_DIR, exist_ok=True)

RESULTADOS = os.path.join(DATA_DIR, "resultados_fiscalia.xlsx")
HISTORIAL = os.path.join(DATA_DIR, "historial_consultas.xlsx")


COLUMNAS_HISTORIAL = ["cedula", "nombre", "metodo", "fecha_consulta"]

COLUMNAS_RESULTADOS = [
    "numero_noticia",
    "cedula_dashboard",
    "nombre_dashboard",
    "metodo_busqueda",
    "fecha",
    "lugar",
    "delito",
    "rol_persona_busqueda",
    "cedula_sujeto",
    "nombre_sujeto",
    "observacion",
    "fecha_consulta",
]


# ==============================
# HISTORIAL (caché en memoria + escritura por lotes)
# ==============================
#
# El historial se lee del disco UNA sola vez. Los registros nuevos se
# acumulan en memoria y se escriben a disco cada GUARDAR_CADA personas
# (y siempre al final con flush_historial). Con ~3000 personas esto
# reduce las escrituras de 3000 a ~300.

_historial_filas = None      # list[dict]
_historial_cedulas = None    # set[str] para búsqueda O(1)
_pendientes = 0


def _cargar_historial():
    global _historial_filas, _historial_cedulas

    if _historial_filas is not None:
        return

    if os.path.exists(HISTORIAL):
        df = leer_excel_seguro(HISTORIAL, dtype={"cedula": str})
        if "cedula" in df.columns:
            df["cedula"] = df["cedula"].apply(normalizar_cedula)
            _historial_filas = df.to_dict("records")
        else:
            _historial_filas = []
    else:
        _historial_filas = []

    _historial_cedulas = {
        f["cedula"] for f in _historial_filas if f.get("cedula")
    }


def cedulas_consultadas():
    """Set de cédulas (normalizadas) ya consultadas."""
    _cargar_historial()
    return set(_historial_cedulas)


def ya_consultado(cedula):
    _cargar_historial()
    return normalizar_cedula(cedula) in _historial_cedulas


def _escribir_historial():
    df = pd.DataFrame(_historial_filas, columns=COLUMNAS_HISTORIAL)
    df.drop_duplicates(subset=["cedula"], keep="last", inplace=True)
    guardar_excel_seguro(df, HISTORIAL)


def registrar_consulta(cedula, nombre, metodo="FINALIZADO"):
    global _pendientes

    _cargar_historial()

    cedula_norm = normalizar_cedula(cedula)

    _historial_filas.append({
        "cedula": cedula_norm,
        "nombre": nombre,
        "metodo": metodo,
        "fecha_consulta": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    if cedula_norm:
        _historial_cedulas.add(cedula_norm)

    _pendientes += 1

    if _pendientes >= GUARDAR_CADA:
        _escribir_historial()
        _pendientes = 0
        print("📝 Historial guardado a disco")


def flush_historial():
    """Escribe a disco lo pendiente. Llamar SIEMPRE al terminar."""
    global _pendientes

    if _historial_filas is not None and _pendientes > 0:
        _escribir_historial()
        _pendientes = 0
        print("📝 Historial final guardado")


# ==============================
# GUARDAR RESULTADOS
# ==============================

def guardar_resultados(resultados):
    if not resultados:
        return

    fecha_consulta = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    filas = [
        {
            "numero_noticia": r.get("numero_noticia", ""),
            "cedula_dashboard": normalizar_cedula(r.get("cedula_busqueda", "")),
            "nombre_dashboard": r.get("nombre_dashboard", ""),
            "metodo_busqueda": r.get("metodo_busqueda", ""),
            "fecha": r.get("fecha", ""),
            "lugar": r.get("lugar", ""),
            "delito": r.get("delito", ""),
            "rol_persona_busqueda": r.get("rol_persona_busqueda", ""),
            "cedula_sujeto": normalizar_cedula(r.get("cedula_sujeto", "")),
            "nombre_sujeto": r.get("nombre_sujeto", ""),
            "observacion": r.get("observacion", ""),
            "fecha_consulta": fecha_consulta,
        }
        for r in resultados
    ]

    nuevo = pd.DataFrame(filas, columns=COLUMNAS_RESULTADOS)

    if os.path.exists(RESULTADOS):
        actual = leer_excel_seguro(RESULTADOS, dtype={"cedula_dashboard": str})
        nuevo = pd.concat([actual, nuevo], ignore_index=True)

    nuevo.drop_duplicates(
        subset=["numero_noticia", "cedula_dashboard"],
        keep="last",
        inplace=True,
    )

    guardar_excel_seguro(nuevo, RESULTADOS)

    print("✅ Resultados Fiscalía guardados")
