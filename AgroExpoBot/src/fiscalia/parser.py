import re

try:
    from utils.cedula import normalizar_cedula
except ImportError:
    from src.utils.cedula import normalizar_cedula


# ==========================================
# EXTRAER NOTICIAS
# ==========================================

REGEX_SUJETO = re.compile(
    r"(\d{10})\s+(.+?)\s+("
    r"DENUNCIANTE|"
    r"SOSPECHOSO NO RECONOCIDO|"
    r"SOSPECHOSO|"
    r"INVESTIGADO|"
    r"PROCESADO|"
    r"ACUSADO|"
    r"IMPUTADO|"
    r"DENUNCIADO|"
    r"PRESUNTO RESPONSABLE|"
    r"RESPONSABLE|"
    r"CONDUCTOR|"
    r"PARTICIPE|"
    r"PARTÍCIPE|"
    r"VICTIMA|"
    r"VÍCTIMA|"
    r"TESTIGO|"
    r"AFECTADO|"
    r"NN"
    r")",
    re.I,
)


def extraer_noticias(texto, cedula=None):
    noticias = []

    bloques = re.split(r"NOTICIA DEL DELITO Nro\.", texto)

    for bloque in bloques[1:]:

        noticia = {
            "numero_noticia": "",
            "fecha": "",
            "lugar": "",
            "delito": "",
            "sujetos": [],
        }

        # El número de la noticia viene inmediatamente después de "Nro.".
        # Si no está al inicio del bloque, como respaldo se busca un número
        # largo (12+ dígitos) para no confundirlo con una cédula (10 dígitos).
        numero = re.match(r"\s*:?\s*(\d{10,20})", bloque)
        if not numero:
            numero = re.search(r"(\d{12,20})", bloque)

        if numero:
            noticia["numero_noticia"] = numero.group(1)

        fecha = re.search(r"FECHA\s+(\d{4}-\d{2}-\d{2})", bloque)
        if fecha:
            noticia["fecha"] = fecha.group(1)

        lugar = re.search(r"LUGAR\s+(.+?)\s+FECHA", bloque, re.S)
        if lugar:
            noticia["lugar"] = lugar.group(1).replace("\n", " ").strip()

        delito = re.search(r"DELITO:\s*(.+)", bloque)
        if delito:
            noticia["delito"] = delito.group(1).split("\n")[0].strip()

        # Sujetos. Captura líneas como:
        #   0912823135 NOMBRE APELLIDO DENUNCIANTE
        #   0000000000 NN SOSPECHOSO NO RECONOCIDO
        for ced, nombre, rol in REGEX_SUJETO.findall(bloque):
            noticia["sujetos"].append({
                "cedula": ced.strip(),
                "nombre": nombre.strip(),
                "rol": rol.strip().upper(),
            })

        noticias.append(noticia)

    return noticias


# ==========================================
# BUSCAR PERSONA
# ==========================================

def obtener_persona_buscada(noticia, cedula_busqueda):
    cedula_busqueda = normalizar_cedula(cedula_busqueda)

    for sujeto in noticia.get("sujetos", []):
        if normalizar_cedula(sujeto.get("cedula", "")) == cedula_busqueda:
            return sujeto

    return None


# ==========================================
# ROLES
# ==========================================

ROLES_RELEVANTES = [
    "SOSPECHOSO",
    "INVESTIGADO",
    "PROCESADO",
    "ACUSADO",
    "IMPUTADO",
    "DENUNCIADO",
    "RESPONSABLE",
    "PRESUNTO RESPONSABLE",
    "AUTOR",
    "PARTICIPE",
    "CONDUCTOR",
]


def es_rol_relevante(rol):
    rol = str(rol).upper()
    return any(r in rol for r in ROLES_RELEVANTES)
