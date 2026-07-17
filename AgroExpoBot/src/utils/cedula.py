"""Normalización de cédulas — única fuente de verdad para todo el proyecto."""


def normalizar_cedula(cedula):
    """Devuelve la cédula como texto de 10 dígitos (rellena ceros a la izquierda).

    Acepta números, strings con ".0" (efecto Excel), NaN/None.
    Devuelve "" si no contiene dígitos.
    """
    if cedula is None:
        return ""

    s = str(cedula).strip()

    if not s or s.lower() in ("nan", "<na>", "nat", "none"):
        return ""

    if s.endswith(".0"):
        s = s[:-2]

    s = "".join(c for c in s if c.isdigit())

    if not s:
        return ""

    return s.zfill(10)
