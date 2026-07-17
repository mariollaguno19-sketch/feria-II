import os
import pandas as pd

try:
    from utils.cedula import normalizar_cedula as limpiar_cedula
    from utils.seguridad import leer_excel_seguro, guardar_excel_seguro
except ImportError:
    from src.utils.cedula import normalizar_cedula as limpiar_cedula
    from src.utils.seguridad import leer_excel_seguro, guardar_excel_seguro

# Ruta del archivo Excel
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
ARCHIVO_EXCEL = os.path.join(DATA_DIR, "registros_dashboard.xlsx")

# Crear carpeta data si no existe
os.makedirs(DATA_DIR, exist_ok=True)


def actualizar_excel(registros):
    """
    Guarda o actualiza el Excel con los registros del dashboard de forma segura
    (cifrado en reposo y escritura atómica).
    """

    nuevos = pd.DataFrame(registros)
    if "cedula" in nuevos.columns:
        nuevos["cedula"] = nuevos["cedula"].apply(limpiar_cedula)

    if os.path.exists(ARCHIVO_EXCEL):
        # Lee asegurando que la cédula sea string para no perder ceros a la izquierda
        actuales = leer_excel_seguro(ARCHIVO_EXCEL, dtype={"cedula": str})
        if "cedula" in actuales.columns:
            actuales["cedula"] = actuales["cedula"].apply(limpiar_cedula)

        combinado = pd.concat(
            [actuales, nuevos],
            ignore_index=True
        )

        combinado.drop_duplicates(
            subset=["cedula"],
            keep="last",
            inplace=True
        )
    else:
        combinado = nuevos

    guardar_excel_seguro(combinado, ARCHIVO_EXCEL)

    print("\n===================================")
    print("✅ Excel actualizado correctamente")
    print("📄 Archivo:", ARCHIVO_EXCEL)
    print("👥 Total registros:", len(combinado))
    print("===================================")
