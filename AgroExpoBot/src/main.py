import re
import sys

from playwright.sync_api import sync_playwright
from actualizar_excel import actualizar_excel

# En Windows la consola puede usar cp1252 y los prints con emojis
# lanzan UnicodeEncodeError; se fuerza UTF-8 con reemplazo seguro.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

try:
    from utils.config import HEADLESS
except ImportError:
    try:
        from src.utils.config import HEADLESS
    except ImportError:
        HEADLESS = True

BASE_URL = "https://core-it.ec/registroexpo/agroexpo2026.php?view=registros&page={}"


def obtener_ultima_pagina(page):
    """Obtiene el número de la última página del dashboard de forma eficiente."""

    page.goto(BASE_URL.format(1))
    page.wait_for_load_state("networkidle")

    print("\n========== BUSCANDO ÚLTIMA PÁGINA ==========")

    # Extrae todos los hrefs de paginación en una sola llamada IPC
    hrefs = page.evaluate("""() => {
        const enlaces = document.querySelectorAll(".pagination a");
        return Array.from(enlaces).map(el => el.getAttribute("href"));
    }""")

    ultima = 1

    for href in hrefs:
        if href:
            m = re.search(r"page=(\d+)", href)
            if m:
                numero = int(m.group(1))
                if numero > ultima:
                    ultima = numero

    print("Última página:", ultima)
    return ultima


def leer_pagina(page, numero):
    """Lee todos los registros de una página de forma optimizada con evaluate()."""

    print(f"\nLeyendo página {numero}...")
    page.goto(BASE_URL.format(numero))
    page.wait_for_load_state("networkidle")

    # Extrae el contenido de todas las celdas de la tabla en un solo viaje redondo IPC
    datos_filas = page.evaluate("""() => {
        const filas = document.querySelectorAll("#registrosTable tbody tr");
        return Array.from(filas).map(fila => {
            const columnas = fila.querySelectorAll("td");
            return Array.from(columnas).map(col => col.innerText.trim());
        });
    }""")

    registros = []
    print("Registros encontrados:", len(datos_filas))

    for datos in datos_filas:
        registro = {
            "cedula": datos[0] if len(datos) > 0 else "",
            "nombre": datos[1] if len(datos) > 1 else "",
            "empresa": datos[2] if len(datos) > 2 else "",
            "cargo": datos[3] if len(datos) > 3 else "",
            "celular": datos[4] if len(datos) > 4 else "",
            "correo": datos[5] if len(datos) > 5 else "",
            "fecha_ingreso": datos[6] if len(datos) > 6 else "",
            "estado": datos[7] if len(datos) > 7 else "",
            "asistencia": datos[8] if len(datos) > 8 else ""
        }
        registros.append(registro)

    return registros


def iniciar():
    with sync_playwright() as p:
        print(f"Iniciando navegador (headless={HEADLESS})...")
        navegador = p.chromium.launch(headless=HEADLESS)
        pagina = navegador.new_page()

        ultima = obtener_ultima_pagina(pagina)
        todos = []

        for numero in range(ultima, 0, -1):
            registros = leer_pagina(pagina, numero)
            todos.extend(registros)

        print("\n===================================")
        print("TOTAL DE PERSONAS:", len(todos))
        print("===================================")

        actualizar_excel(todos)
        navegador.close()


if __name__ == "__main__":
    iniciar()