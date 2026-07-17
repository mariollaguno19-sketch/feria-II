"""Protección de los datos personales del proyecto.

- Cifrado en reposo (Fernet/AES) de los Excel con datos de personas.
- La clave vive en ~/.agroexpobot/clave.key: FUERA de la carpeta del
  proyecto, de OneDrive y de git, así una copia del proyecto o del repo
  no expone los datos.
- Escritura atómica: se escribe a un archivo temporal y luego se
  reemplaza, para que un corte de luz no corrompa el historial.
- Enmascaramiento de cédulas para los logs.

Uso desde consola:
    python -m src.utils.seguridad exportar   -> copia descifrada en data/descifrado/
    python -m src.utils.seguridad cifrar     -> cifra los Excel que estén en claro
"""

import io
import os
import sys

import pandas as pd

# En Windows la consola puede usar cp1252 y los prints con emojis
# lanzan UnicodeEncodeError; se fuerza UTF-8 con reemplazo seguro.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

try:
    from cryptography.fernet import Fernet, InvalidToken
except ImportError as e:
    raise ImportError(
        "Falta el paquete 'cryptography'. Instálalo con: pip install cryptography"
    ) from e

try:
    from utils.config import CIFRAR_DATOS
except ImportError:
    try:
        from src.utils.config import CIFRAR_DATOS
    except ImportError:
        CIFRAR_DATOS = True


# Los .xlsx en claro empiezan con la firma ZIP "PK"; los cifrados no.
_FIRMA_XLSX = b"PK"

RUTA_CLAVE = os.path.join(os.path.expanduser("~"), ".agroexpobot", "clave.key")


def _obtener_clave():
    """Carga la clave de cifrado; la genera la primera vez."""
    if os.path.exists(RUTA_CLAVE):
        with open(RUTA_CLAVE, "rb") as f:
            return f.read().strip()

    os.makedirs(os.path.dirname(RUTA_CLAVE), exist_ok=True)
    clave = Fernet.generate_key()
    with open(RUTA_CLAVE, "wb") as f:
        f.write(clave)

    print(f"🔑 Clave de cifrado generada en {RUTA_CLAVE}")
    print("   ⚠ Respáldala en un lugar seguro: sin ella no se pueden leer los datos.")
    return clave


def _fernet():
    return Fernet(_obtener_clave())


def esta_cifrado(ruta):
    with open(ruta, "rb") as f:
        return f.read(2) != _FIRMA_XLSX


def leer_excel_seguro(ruta, **kwargs):
    """Lee un Excel cifrado o en claro (migración transparente)."""
    with open(ruta, "rb") as f:
        datos = f.read()

    if not datos.startswith(_FIRMA_XLSX):
        try:
            datos = _fernet().decrypt(datos)
        except InvalidToken:
            raise RuntimeError(
                f"No se pudo descifrar {ruta}: la clave en {RUTA_CLAVE} no corresponde."
            )

    return pd.read_excel(io.BytesIO(datos), **kwargs)


def guardar_excel_seguro(df, ruta):
    """Guarda un DataFrame como Excel cifrado (si CIFRAR_DATOS) y de forma atómica."""
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)
    datos = buffer.getvalue()

    if CIFRAR_DATOS:
        datos = _fernet().encrypt(datos)

    tmp = ruta + ".tmp"
    with open(tmp, "wb") as f:
        f.write(datos)
    os.replace(tmp, ruta)


def mask_cedula(cedula):
    """Enmascara una cédula para logs: 0912823135 -> 091****135."""
    s = str(cedula or "")
    if len(s) < 7:
        return "***"
    return s[:3] + "*" * (len(s) - 6) + s[-3:]


# ==========================================
# CLI: cifrar / exportar
# ==========================================

def _archivos_data():
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data = os.path.join(base, "data")
    if not os.path.isdir(data):
        return data, []
    return data, [
        os.path.join(data, n)
        for n in os.listdir(data)
        if n.endswith(".xlsx")
    ]


def cifrar_todo():
    _, archivos = _archivos_data()
    for ruta in archivos:
        if esta_cifrado(ruta):
            print(f"🔒 Ya cifrado: {os.path.basename(ruta)}")
            continue
        df = pd.read_excel(ruta)
        guardar_excel_seguro(df, ruta)
        print(f"🔐 Cifrado: {os.path.basename(ruta)}")


def exportar_todo():
    data, archivos = _archivos_data()
    destino = os.path.join(data, "descifrado")
    os.makedirs(destino, exist_ok=True)

    for ruta in archivos:
        df = leer_excel_seguro(ruta)
        salida = os.path.join(destino, os.path.basename(ruta))
        df.to_excel(salida, index=False)
        print(f"📂 Exportado: {salida}")

    print("\n⚠ Las copias en data/descifrado/ están EN CLARO para revisión.")
    print("  Bórralas cuando termines de usarlas.")


if __name__ == "__main__":
    accion = sys.argv[1] if len(sys.argv) > 1 else ""
    if accion == "cifrar":
        cifrar_todo()
    elif accion == "exportar":
        exportar_todo()
    else:
        print("Uso: python -m src.utils.seguridad [cifrar|exportar]")
