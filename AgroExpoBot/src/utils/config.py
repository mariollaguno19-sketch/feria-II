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


# ===============================
# SEGURIDAD DE LA INFORMACIÓN
# ===============================

# Cifra los Excel de data/ en reposo (clave en ~/.agroexpobot/clave.key).
# Para ver los archivos: python -m src.utils.seguridad exportar
CIFRAR_DATOS = True

# Enmascara las cédulas en la consola (091****135)
ENMASCARAR_LOGS = True

# Logs detallados de comparación de nombres (solo para depurar)
DEBUG = False


# ===============================
# ESCALA (hasta ~3000 personas)
# ===============================

# Guardar el historial a disco cada N personas procesadas
# (menos escrituras = mucho más rápido; máximo se pierden N-1
#  consultas si se corta la luz, y solo se re-consultarían).
GUARDAR_CADA = 10

# Reiniciar el navegador cada N búsquedas para evitar fugas de
# memoria y sesiones degradadas en corridas largas.
REINICIAR_NAVEGADOR_CADA = 250

# Reintentos por persona ante un fallo puntual (red, iframe caído)
REINTENTOS_PERSONA = 2

# Pausa entre personas (ms) para no saturar el portal de la Fiscalía
PAUSA_ENTRE_PERSONAS = 300
