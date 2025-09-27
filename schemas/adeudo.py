def adeudo_schema(adeudo) -> dict:
    return {
        "venta_id":adeudo["venta_id"],
        "monto_pendiente":float(adeudo["monto_pendiente"].to_decimal()),
    }

def adeudos_schema(adeudos) -> list:
    return [adeudo_schema(adeudo) for adeudo in adeudos]