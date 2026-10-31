"""ERP · Evaluaciones: reglas puras de calificación (1 a 5 estrellas)."""


def validar_estrellas(valor):
    try:
        if isinstance(valor, bool):
            raise ValueError
        n = int(valor)
    except (TypeError, ValueError):
        raise ValueError("las estrellas van de 1 a 5")
    if not 1 <= n <= 5:
        raise ValueError("las estrellas van de 1 a 5")
    return n


def validar_comentario(texto):
    texto = texto.strip() if isinstance(texto, str) else ""
    if len(texto) > 300:
        raise ValueError("el comentario no puede pasar de 300 caracteres")
    return texto


def resumen_estrellas(valores):
    valores = list(valores)
    if not valores:
        return {"promedio": None, "total": 0}
    return {"promedio": round(sum(valores) / len(valores), 1), "total": len(valores)}
