import os


# ===============================
# RUTAS DEL PROYECTO
# ===============================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)


DATA_DIR = os.path.join(
    BASE_DIR,
    "data"
)


# ===============================
# ARCHIVO DEL DASHBOARD
# ===============================

# PRODUCCIÓN: procesa todas las personas del dashboard.
# Para pruebas rápidas cambiar a "prueba_dashboard.xlsx" (5 registros).
DASHBOARD_EXCEL = os.path.join(
    DATA_DIR,
    "registros_dashboard.xlsx"
)


# ===============================
# CONFIGURACIÓN PLAYWRIGHT
# ===============================

URL_FISCALIA = (
    "https://www.fiscalia.gob.ec/"
    "accesibilidad/consulta-de-noticias-del-delito/"
)


HEADLESS = True


# Tiempo para cargar Fiscalía
TIMEOUT = 5000


# Tiempo después de presionar Buscar
ESPERA_BUSQUEDA = 3000