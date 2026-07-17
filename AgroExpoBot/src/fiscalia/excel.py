import os
import pandas as pd
from datetime import datetime

try:
    from utils.cedula import normalizar_cedula
except ImportError:
    from src.utils.cedula import normalizar_cedula


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
# HISTORIAL (caché en memoria)
# ==============================
#
# El historial se lee del disco UNA sola vez y luego se mantiene en
# memoria; cada registro nuevo se agrega a la caché y se reescribe el
# archivo (así el avance sobrevive a un corte a mitad del proceso).

_historial_cache = None


def _cargar_historial():
    global _historial_cache

    if _historial_cache is not None:
        return _historial_cache

    if os.path.exists(HISTORIAL):
        df = pd.read_excel(HISTORIAL, dtype={"cedula": str})
        if "cedula" in df.columns:
            df["cedula"] = df["cedula"].apply(normalizar_cedula)
        else:
            df = pd.DataFrame(columns=COLUMNAS_HISTORIAL)
    else:
        df = pd.DataFrame(columns=COLUMNAS_HISTORIAL)

    _historial_cache = df
    return _historial_cache


def ya_consultado(cedula):
    cedula = normalizar_cedula(cedula)
    historial = _cargar_historial()
    return cedula in historial["cedula"].values


def registrar_consulta(cedula, nombre, metodo="FINALIZADO"):
    global _historial_cache

    registro = pd.DataFrame([{
        "cedula": normalizar_cedula(cedula),
        "nombre": nombre,
        "metodo": metodo,
        "fecha_consulta": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }])

    historial = _cargar_historial()

    historial = pd.concat([historial, registro], ignore_index=True)
    historial.drop_duplicates(subset=["cedula"], keep="last", inplace=True)

    _historial_cache = historial
    historial.to_excel(HISTORIAL, index=False)

    print("📝 Consulta registrada en historial")


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
        actual = pd.read_excel(RESULTADOS, dtype={"cedula_dashboard": str})
        nuevo = pd.concat([actual, nuevo], ignore_index=True)

    nuevo.drop_duplicates(
        subset=["numero_noticia", "cedula_dashboard"],
        keep="last",
        inplace=True,
    )

    nuevo.to_excel(RESULTADOS, index=False)

    print("✅ Resultados Fiscalía guardados")
