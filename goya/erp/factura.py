"""ERP · Factura: folio y emisión de la factura de una orden."""
from .total import calcular_total


def formatear_folio(numero):
    return f"GOYA-{numero:06d}"


def emitir_factura(orden, subtotal, metodo_pago, comision_pct):
    from ..extensions import db
    from .models import Factura

    t = calcular_total(subtotal, comision_pct)
    f = Factura(orden_id=orden.id, folio=formatear_folio(orden.id), metodo_pago=metodo_pago,
                subtotal=t["subtotal"], comision=t["comision"], total=t["total"])
    db.session.add(f)
    return f
