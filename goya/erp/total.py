"""ERP · Total: subtotal + comisión de la plataforma."""
from decimal import Decimal, ROUND_HALF_UP

CENTAVO = Decimal("0.01")


def calcular_total(subtotal, comision_pct):
    subtotal = Decimal(str(subtotal)).quantize(CENTAVO, ROUND_HALF_UP)
    if subtotal < 0:
        raise ValueError("subtotal no puede ser negativo")
    comision = (subtotal * Decimal(str(comision_pct)) / 100).quantize(CENTAVO, ROUND_HALF_UP)
    return {"subtotal": subtotal, "comision": comision, "total": subtotal + comision}
