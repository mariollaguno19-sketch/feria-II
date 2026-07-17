def nombre_valido_para_busqueda(nombre):
    """Un nombre es buscable si está completo: mínimo nombre + dos apellidos."""
    if not nombre:
        return False

    return len(nombre.strip().split()) >= 3
