import re
import sys
import time

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
    flush_historial,
    cedulas_consultadas,
)
from src.utils.cedula import normalizar_cedula
from src.utils.seguridad import leer_excel_seguro, mask_cedula
from src.utils.config import (
    DASHBOARD_EXCEL,
    ENMASCARAR_LOGS,
    REINICIAR_NAVEGADOR_CADA,
    REINTENTOS_PERSONA,
    PAUSA_ENTRE_PERSONAS,
)
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


def _cedula_log(cedula):
    """Cédula para consola: enmascarada salvo que se desactive en config."""
    return mask_cedula(cedula) if ENMASCARAR_LOGS else str(cedula)


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
    print("Cédula:", _cedula_log(cedula))
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


def _procesar_con_reintentos(buscador, cedula, nombre):
    """Reintenta ante fallos puntuales, reiniciando el navegador entre intentos."""
    ultimo_error = None

    for intento in range(1, REINTENTOS_PERSONA + 1):
        try:
            return procesar_persona(buscador, cedula, nombre)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            ultimo_error = e
            print(f"⚠ Intento {intento}/{REINTENTOS_PERSONA} falló: {e}")
            if intento < REINTENTOS_PERSONA:
                buscador.reiniciar()

    raise ultimo_error


def _eta(inicio, hechas, restantes):
    if hechas == 0:
        return "?"
    segundos = (time.time() - inicio) / hechas * restantes
    return f"{int(segundos // 3600)}h {int(segundos % 3600 // 60):02d}m"


def iniciar_proceso():
    personas = leer_excel_seguro(DASHBOARD_EXCEL, dtype={"cedula": str})
    total = len(personas)

    print("==============================")
    print("TOTAL PERSONAS:", total)
    print("==============================")

    consultados = cedulas_consultadas()
    print(f"📚 Historial cargado: {len(consultados)} personas ya consultadas.")

    buscador = BuscadorFiscalia()
    errores = []
    procesadas = 0
    busquedas = 0
    inicio = time.time()

    try:
        buscador.iniciar()

        for i, (_, persona) in enumerate(personas.iterrows(), start=1):
            cedula = str(persona.get("cedula", "")).strip()
            nombre = str(persona.get("nombre", "")).strip()

            if nombre.lower() in ("nan", "none"):
                nombre = ""

            cedula_norm = normalizar_cedula(cedula)

            if not cedula_norm and not nombre_valido_para_busqueda(nombre):
                continue

            if cedula_norm and cedula_norm in consultados:
                continue

            print("\n------------------------------")
            print(f"[{i}/{total}] procesadas: {procesadas}"
                  f" | errores: {len(errores)}"
                  f" | ETA: {_eta(inicio, procesadas, total - i)}")

            # Reinicio preventivo del navegador en corridas largas
            if busquedas > 0 and busquedas % REINICIAR_NAVEGADOR_CADA == 0:
                buscador.reiniciar()

            try:
                resultados = _procesar_con_reintentos(buscador, cedula, nombre)
            except KeyboardInterrupt:
                print("\n⛔ Interrumpido por el usuario, guardando avance...")
                raise
            except Exception as e:
                print(f"❌ Error procesando {_cedula_log(cedula)} - {nombre}: {e}")
                errores.append((cedula, nombre, str(e)))
                continue

            busquedas += 1
            procesadas += 1

            if resultados:
                guardar_resultados(resultados)
            else:
                print("Sin coincidencias relevantes")

            registrar_consulta(cedula, nombre, "FINALIZADO")
            consultados.add(cedula_norm)

            if PAUSA_ENTRE_PERSONAS:
                time.sleep(PAUSA_ENTRE_PERSONAS / 1000)

    finally:
        # Pase lo que pase: el avance pendiente queda en disco
        flush_historial()
        buscador.cerrar()

    print("\n==============================")
    print(f"FIN: {procesadas} procesadas, {len(errores)} con error")
    print("==============================")

    if errores:
        print("⚠️ Personas con error (se reintentan en la próxima corrida):")
        for cedula, nombre, error in errores:
            print(f"  - {_cedula_log(cedula)} {nombre}: {error}")


if __name__ == "__main__":
    iniciar_proceso()
