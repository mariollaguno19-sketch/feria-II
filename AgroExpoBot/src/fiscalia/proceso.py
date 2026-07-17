import re
import sys

import pandas as pd

# En Windows la consola puede usar cp1252 y los prints con emojis
# lanzan UnicodeEncodeError; se fuerza UTF-8 con reemplazo seguro.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

from src.fiscalia.buscador import BuscadorFiscalia
from src.fiscalia.parser import extraer_noticias
from src.fiscalia.excel import (
    registrar_consulta,
    guardar_resultados,
    _cargar_historial,
)
from src.utils.cedula import normalizar_cedula
from src.utils.config import DASHBOARD_EXCEL
from src.utils.nombres import nombre_valido_para_busqueda
from src.fiscalia.comparador_nombres import comparar_nombres


ROLES_IGNORADOS = [
    "DENUNCIANTE",
    "VICTIMA",
    "VÍCTIMA",
    "TESTIGO",
    "PERJUDICADO",
    "AFECTADO",
]

ROLES_VALIDOS = [
    "SOSPECHOSO",
    "INVESTIGADO",
    "PROCESADO",
    "ACUSADO",
    "IMPUTADO",
    "DENUNCIADO",
    "AUTOR",
    "PARTICIPE",
    "RESPONSABLE",
    "CAUSANTE",
    "INVOLUCRADO",
]

DELITOS_TRANSITO = [
    "TRANSITO",
    "TRÁNSITO",
    "ACCIDENTE",
    "CHOQUE",
    "COLISION",
    "COLISIÓN",
    "DAÑOS MATERIALES",
]


def limpiar_delito(delito):
    if not delito:
        return ""
    return re.sub(r"\(\d+\)", "", str(delito)).strip()


def delito_transito(delito):
    delito = limpiar_delito(delito).upper()
    return any(palabra in delito for palabra in DELITOS_TRANSITO)


def rol_valido(rol):
    rol = str(rol).upper()
    return any(r in rol for r in ROLES_VALIDOS)


def analizar_noticias(noticias, cedula, nombre, metodo):
    """Filtra las noticias donde la persona buscada aparece con un rol relevante."""

    resultados = []
    cedula_norm = normalizar_cedula(cedula)

    print("Noticias analizadas:", len(noticias))

    for noticia in noticias:

        delito = noticia.get("delito", "")

        if delito_transito(delito):
            print("⚠ Delito tránsito ignorado:", limpiar_delito(delito))
            continue

        for sujeto in noticia.get("sujetos", []):

            cedula_sujeto = str(sujeto.get("cedula", "")).strip()
            nombre_sujeto = str(sujeto.get("nombre", "")).strip()
            rol = str(sujeto.get("rol", "")).upper()

            if any(x in rol for x in ROLES_IGNORADOS):
                continue

            # Coincidencia por cédula (ambas normalizadas para no perder
            # coincidencias por ceros a la izquierda), o por nombre si el
            # nombre del dashboard está completo.
            coincide = (
                cedula_norm != ""
                and normalizar_cedula(cedula_sujeto) == cedula_norm
            )

            if not coincide and nombre_valido_para_busqueda(nombre):
                if comparar_nombres(nombre, nombre_sujeto, minimo_palabras=3):
                    print("✅ Coincidencia nombre:", nombre_sujeto)
                    coincide = True

            if coincide and rol_valido(rol):
                print("🔥 ENCONTRADO:", nombre_sujeto, "-", rol)

                noticia["es_relevante"] = True
                noticia["rol_persona_busqueda"] = rol
                noticia["cedula_busqueda"] = cedula
                noticia["metodo_busqueda"] = metodo
                noticia["nombre_dashboard"] = nombre
                noticia["delito"] = limpiar_delito(delito)
                noticia["cedula_sujeto"] = cedula_sujeto
                noticia["nombre_sujeto"] = nombre_sujeto

                resultados.append(noticia)
                break

    return resultados


def procesar_persona(buscador, cedula, nombre):
    print("\n------------------------------")
    print("Cédula:", cedula)
    print("Nombre:", nombre)

    cedula_norm = normalizar_cedula(cedula)

    if cedula_norm:
        print("🔎 Buscando por cédula...")

        texto = buscador.buscar_por_cedula(cedula_norm)
        noticias = extraer_noticias(texto)
        resultados = analizar_noticias(noticias, cedula, nombre, "CEDULA")

        if resultados:
            return resultados

    if nombre_valido_para_busqueda(nombre):
        print("⚠ Sin resultados relevantes por cédula")
        print("🔎 Buscando por nombre...")

        texto = buscador.buscar_por_nombre(nombre)
        noticias = extraer_noticias(texto)
        return analizar_noticias(noticias, cedula, nombre, "NOMBRE")

    print("❌ Nombre incompleto, no se busca por nombre")
    return []


def iniciar_proceso():
    personas = pd.read_excel(DASHBOARD_EXCEL, dtype={"cedula": str})

    print("==============================")
    print("TOTAL PERSONAS:", len(personas))
    print("==============================")

    # Historial en memoria (se carga una sola vez) para saltar en O(1)
    # a las personas ya consultadas.
    consultados = set(_cargar_historial()["cedula"].dropna().unique())
    consultados.discard("")
    print(f"📚 Historial cargado: {len(consultados)} personas ya consultadas.")

    buscador = BuscadorFiscalia()
    errores = []

    try:
        buscador.iniciar()

        for _, persona in personas.iterrows():
            cedula = str(persona.get("cedula", "")).strip()
            nombre = str(persona.get("nombre", "")).strip()

            if nombre.lower() in ("nan", "none"):
                nombre = ""

            cedula_norm = normalizar_cedula(cedula)

            print("\nPROCESANDO")

            if not cedula_norm and not nombre_valido_para_busqueda(nombre):
                print("⏭ Sin cédula ni nombre completo, se omite")
                continue

            if cedula_norm and cedula_norm in consultados:
                print("⏭ Ya consultado")
                continue

            # Un fallo puntual (red, cambio en la página) no debe abortar
            # todo el proceso: se anota y se sigue con la siguiente persona.
            try:
                resultados = procesar_persona(buscador, cedula, nombre)
            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"❌ Error procesando {cedula} - {nombre}: {e}")
                errores.append((cedula, nombre, str(e)))
                continue

            if resultados:
                guardar_resultados(resultados)
            else:
                print("Sin coincidencias relevantes")

            registrar_consulta(cedula, nombre, "FINALIZADO")
            consultados.add(cedula_norm)

    finally:
        buscador.cerrar()

    if errores:
        print("\n==============================")
        print(f"⚠️ {len(errores)} personas con error (se reintentan en la próxima corrida):")
        for cedula, nombre, error in errores:
            print(f"  - {cedula} {nombre}: {error}")


if __name__ == "__main__":
    iniciar_proceso()
