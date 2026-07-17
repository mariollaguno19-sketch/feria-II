import re
import unicodedata



def normalizar_nombre(nombre):

    if nombre is None:
        return ""


    nombre = str(nombre).upper()


    nombre = unicodedata.normalize(
        "NFD",
        nombre
    )


    nombre = "".join(
        c
        for c in nombre
        if unicodedata.category(c) != "Mn"
    )


    nombre = re.sub(
        r"[^A-ZÑ ]",
        " ",
        nombre
    )


    nombre = " ".join(
        nombre.split()
    )


    return nombre





STOP_WORDS = {"DE", "DEL", "LA", "LAS", "LOS", "Y", "EL"}


def palabras(nombre):
    return set(
        w for w in normalizar_nombre(nombre).split()
        if w not in STOP_WORDS
    )





def comparar_nombres(
    nombre_dashboard,
    nombre_fiscalia,
    minimo_palabras=3
):


    p1 = palabras(
        nombre_dashboard
    )


    p2 = palabras(
        nombre_fiscalia
    )


    comunes = p1.intersection(
        p2
    )


    print(
        "Comparación:",
        p1,
        p2,
        "=>",
        comunes
    )


    return len(comunes) >= minimo_palabras