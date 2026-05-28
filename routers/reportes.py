from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, status, Depends, Query
from core.database import db_client
from validar_token import validar_token, require_permission
from bson import ObjectId
from bson.decimal128 import Decimal128

router = APIRouter(prefix="/reportes", tags=["reportes"])


def _filtro_periodo(periodo: str, f_ini: str = None, f_fin: str = None) -> dict:
    """Genera filtro de fecha según el periodo seleccionado."""
    ahora = datetime.now()
    if periodo == "semana":
        fecha_inicio = ahora - timedelta(days=7)
        return {"fecha_venta": {"$gte": fecha_inicio, "$lte": ahora}}
    elif periodo == "mes":
        fecha_inicio = ahora - timedelta(days=30)
        return {"fecha_venta": {"$gte": fecha_inicio, "$lte": ahora}}
    elif periodo == "custom" and f_ini and f_fin:
        try:
            inicio = datetime.strptime(f_ini[:10], "%Y-%m-%d").replace(hour=0, minute=0, second=0)
            fin = datetime.strptime(f_fin[:10], "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            return {"fecha_venta": {"$gte": inicio, "$lte": fin}}
        except ValueError:
            pass
    # "todo" -> sin filtro de fecha
    return {}


def _filtro_periodo_anterior(periodo: str, f_ini: str = None, f_fin: str = None) -> tuple[dict, str, str]:
    """Genera filtro del periodo anterior para comparativa."""
    ahora = datetime.now()
    if periodo == "semana":
        fecha_fin = ahora - timedelta(days=7)
        fecha_inicio = ahora - timedelta(days=14)
        return {"fecha_venta": {"$gte": fecha_inicio, "$lte": fecha_fin}}, fecha_inicio.strftime("%Y-%m-%d"), fecha_fin.strftime("%Y-%m-%d")
    elif periodo == "mes":
        fecha_fin = ahora - timedelta(days=30)
        fecha_inicio = ahora - timedelta(days=60)
        return {"fecha_venta": {"$gte": fecha_inicio, "$lte": fecha_fin}}, fecha_inicio.strftime("%Y-%m-%d"), fecha_fin.strftime("%Y-%m-%d")
    elif periodo == "custom" and f_ini and f_fin:
        try:
            inicio = datetime.strptime(f_ini[:10], "%Y-%m-%d").replace(hour=0, minute=0, second=0)
            fin = datetime.strptime(f_fin[:10], "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            delta = fin - inicio
            dias = delta.days + 1
            fecha_fin_ant = inicio - timedelta(days=1)
            fecha_fin_ant = fecha_fin_ant.replace(hour=23, minute=59, second=59)
            fecha_inicio_ant = fecha_fin_ant - timedelta(days=dias - 1)
            fecha_inicio_ant = fecha_inicio_ant.replace(hour=0, minute=0, second=0)
            return {"fecha_venta": {"$gte": fecha_inicio_ant, "$lte": fecha_fin_ant}}, fecha_inicio_ant.strftime("%Y-%m-%d"), fecha_fin_ant.strftime("%Y-%m-%d")
        except ValueError:
            pass
    return {}, "", ""


def _base_match(periodo: str, sucursal_id: str | None, f_ini: str = None, f_fin: str = None) -> dict:
    """Filtro base: ventas liquidadas, no canceladas, con filtros de periodo y sucursal."""
    match = {
        "liquidado": True,
        "cancelado": {"$ne": True},
    }
    filtro_fecha = _filtro_periodo(periodo, f_ini, f_fin)
    match.update(filtro_fecha)
    if sucursal_id:
        match["sucursal_id"] = sucursal_id
    return match


def _decimal128_to_float(value) -> float:
    """Convierte Decimal128 a float de forma segura."""
    if isinstance(value, Decimal128):
        return float(value.to_decimal())
    if value is None:
        return 0.0
    return float(value)


# ─────────────────────────────── RESUMEN ───────────────────────────────
@router.get("/resumen")
async def obtener_resumen(
    periodo: str = Query("mes", regex="^(semana|mes|todo|custom)$"),
    fecha_inicio: str = None,
    fecha_fin: str = None,
    sucursal_id: str = None,
    token: dict = Depends(require_permission("elevado")),
):
    try:
        match = _base_match(periodo, sucursal_id, fecha_inicio, fecha_fin)

        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": None,
                    "total_vendido": {"$sum": "$total"},
                    "numero_ventas": {"$sum": 1},
                    "total_recibido_mxn": {"$sum": {"$ifNull": ["$recibido_mxn", 0]}},
                    "total_recibido_us": {"$sum": {"$ifNull": ["$recibido_us", 0]}},
                    "total_recibido_tarj": {"$sum": {"$ifNull": ["$recibido_tarj", 0]}},
                    "total_recibido_trans": {"$sum": {"$ifNull": ["$recibido_trans", 0]}},
                }
            },
        ]

        resultado = list(db_client.pbstation.ventas.aggregate(pipeline))

        if resultado:
            r = resultado[0]
            total_vendido = _decimal128_to_float(r["total_vendido"])
            numero_ventas = r["numero_ventas"]
            ticket_promedio = total_vendido / numero_ventas if numero_ventas > 0 else 0
        else:
            total_vendido = 0
            numero_ventas = 0
            ticket_promedio = 0

        # Cancelaciones del periodo
        match_canceladas = {
            "cancelado": True,
        }
        filtro_fecha = _filtro_periodo(periodo, fecha_inicio, fecha_fin)
        match_canceladas.update(filtro_fecha)
        if sucursal_id:
            match_canceladas["sucursal_id"] = sucursal_id

        pipeline_cancel = [
            {"$match": match_canceladas},
            {
                "$group": {
                    "_id": None,
                    "total_cancelado": {"$sum": "$total"},
                    "ventas_canceladas": {"$sum": 1},
                }
            },
        ]
        resultado_cancel = list(db_client.pbstation.ventas.aggregate(pipeline_cancel))
        total_cancelado = _decimal128_to_float(resultado_cancel[0]["total_cancelado"]) if resultado_cancel else 0
        ventas_canceladas = resultado_cancel[0]["ventas_canceladas"] if resultado_cancel else 0

        # Adeudos activos (sin filtro de periodo, son actuales)
        match_adeudos = {
            "liquidado": False,
            "cancelado": {"$ne": True},
        }
        if sucursal_id:
            match_adeudos["sucursal_id"] = sucursal_id

        pipeline_adeudos = [
            {"$match": match_adeudos},
            {
                "$group": {
                    "_id": None,
                    "adeudos_activos": {"$sum": "$total"},
                    "num_adeudos": {"$sum": 1},
                }
            },
        ]
        resultado_adeudos = list(db_client.pbstation.ventas.aggregate(pipeline_adeudos))
        adeudos_activos = _decimal128_to_float(resultado_adeudos[0]["adeudos_activos"]) if resultado_adeudos else 0
        num_adeudos = resultado_adeudos[0]["num_adeudos"] if resultado_adeudos else 0

        # Periodo anterior para comparativa
        periodo_anterior = None
        if periodo != "todo":
            match_anterior = {
                "liquidado": True,
                "cancelado": {"$ne": True},
            }
            filtro_anterior, f_ini_ant, f_fin_ant = _filtro_periodo_anterior(periodo, fecha_inicio, fecha_fin)
            match_anterior.update(filtro_anterior)
            if sucursal_id:
                match_anterior["sucursal_id"] = sucursal_id

            if filtro_anterior: # Si logramos calcular fechas
                pipeline_anterior = [
                    {"$match": match_anterior},
                    {
                        "$group": {
                            "_id": None,
                            "total_vendido": {"$sum": "$total"},
                            "numero_ventas": {"$sum": 1},
                        }
                    },
                ]
                resultado_anterior = list(db_client.pbstation.ventas.aggregate(pipeline_anterior))
                if resultado_anterior:
                    ra = resultado_anterior[0]
                    tv_ant = _decimal128_to_float(ra["total_vendido"])
                    nv_ant = ra["numero_ventas"]
                    periodo_anterior = {
                        "total_vendido": round(tv_ant, 2),
                        "numero_ventas": nv_ant,
                        "ticket_promedio": round(tv_ant / nv_ant, 2) if nv_ant > 0 else 0,
                        "fecha_inicio": f_ini_ant,
                        "fecha_fin": f_fin_ant,
                    }
                else:
                    periodo_anterior = {
                        "total_vendido": 0,
                        "numero_ventas": 0,
                        "ticket_promedio": 0,
                        "fecha_inicio": f_ini_ant,
                        "fecha_fin": f_fin_ant,
                    }

        return {
            "total_vendido": round(total_vendido, 2),
            "numero_ventas": numero_ventas,
            "ticket_promedio": round(ticket_promedio, 2),
            "total_cancelado": round(total_cancelado, 2),
            "ventas_canceladas": ventas_canceladas,
            "adeudos_activos": round(adeudos_activos, 2),
            "num_adeudos": num_adeudos,
            "periodo_anterior": periodo_anterior,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener resumen: {str(e)}",
        )


# ─────────────────────────── PRODUCTOS TOP ─────────────────────────────
@router.get("/productos-top")
async def obtener_productos_top(
    periodo: str = Query("mes", regex="^(semana|mes|todo|custom)$"),
    fecha_inicio: str = None,
    fecha_fin: str = None,
    sucursal_id: str = None,
    limite: int = 10,
    token: dict = Depends(require_permission("elevado")),
):
    try:
        match = _base_match(periodo, sucursal_id, fecha_inicio, fecha_fin)
        match["was_deuda"] = {"$ne": True}

        pipeline = [
            {"$match": match},
            {"$unwind": "$detalles"},
            {
                "$group": {
                    "_id": "$detalles.producto_id",
                    "cantidad": {"$sum": "$detalles.cantidad"},
                    "total": {"$sum": "$detalles.total"},
                    "subtotal": {"$sum": "$detalles.subtotal"},
                }
            },
            {"$sort": {"cantidad": -1}},
            {"$limit": limite},
        ]

        resultado = list(db_client.pbstation.ventas.aggregate(pipeline))

        productos_ids = [r["_id"] for r in resultado if r["_id"]]
        productos_map = {}
        if productos_ids:
            productos_cursor = db_client.pbstation.productos.find(
                {"_id": {"$in": [ObjectId(pid) for pid in productos_ids]}},
                {"descripcion": 1}
            )
            productos_map = {str(p["_id"]): p.get("descripcion", "Sin descripción") for p in productos_cursor}

        productos_top = []
        for r in resultado:
            producto_id = r["_id"]
            productos_top.append({
                "producto_id": producto_id,
                "descripcion": productos_map.get(producto_id, "Producto eliminado"),
                "cantidad": r["cantidad"],
                "total": round(_decimal128_to_float(r["total"]), 2),
                "subtotal": round(_decimal128_to_float(r["subtotal"]), 2),
            })

        return productos_top

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener productos top: {str(e)}",
        )


# ─────────────────────────── CLIENTES TOP ──────────────────────────────
@router.get("/clientes-top")
async def obtener_clientes_top(
    periodo: str = Query("mes", regex="^(semana|mes|todo|custom)$"),
    fecha_inicio: str = None,
    fecha_fin: str = None,
    sucursal_id: str = None,
    limite: int = 10,
    token: dict = Depends(require_permission("elevado")),
):
    try:
        match = _base_match(periodo, sucursal_id, fecha_inicio, fecha_fin)
        match["was_deuda"] = {"$ne": True}

        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": "$cliente_id",
                    "total_compras": {"$sum": "$total"},
                    "num_compras": {"$sum": 1},
                    "ticket_promedio": {"$avg": "$total"},
                }
            },
            {"$sort": {"total_compras": -1}},
            {"$limit": limite},
        ]

        resultado = list(db_client.pbstation.ventas.aggregate(pipeline))

        clientes_ids = [r["_id"] for r in resultado if r["_id"]]
        clientes_map = {}
        if clientes_ids:
            clientes_cursor = db_client.pbstation.clientes.find(
                {"_id": {"$in": [ObjectId(cid) for cid in clientes_ids]}},
                {"nombre": 1}
            )
            clientes_map = {str(c["_id"]): c.get("nombre", "Sin nombre") for c in clientes_cursor}

        clientes_top = []
        for r in resultado:
            cliente_id = r["_id"]
            clientes_top.append({
                "cliente_id": cliente_id,
                "nombre": clientes_map.get(cliente_id, "Cliente eliminado"),
                "total_compras": round(_decimal128_to_float(r["total_compras"]), 2),
                "num_compras": r["num_compras"],
                "ticket_promedio": round(_decimal128_to_float(r["ticket_promedio"]), 2),
            })

        return clientes_top

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener clientes top: {str(e)}",
        )


# ─────────────────────────── MÉTODOS DE PAGO ───────────────────────────
@router.get("/metodos-pago")
async def obtener_metodos_pago(
    periodo: str = Query("mes", regex="^(semana|mes|todo|custom)$"),
    fecha_inicio: str = None,
    fecha_fin: str = None,
    sucursal_id: str = None,
    token: dict = Depends(require_permission("elevado")),
):
    try:
        match = _base_match(periodo, sucursal_id, fecha_inicio, fecha_fin)
        match["was_deuda"] = {"$ne": True}

        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": None,
                    "efectivo_mxn": {"$sum": {"$ifNull": ["$recibido_mxn", 0]}},
                    "efectivo_us": {"$sum": {"$ifNull": ["$recibido_us", 0]}},
                    "tarjeta_debito": {
                        "$sum": {
                            "$cond": [
                                {"$eq": ["$tipo_tarjeta", "debito"]},
                                {"$ifNull": ["$recibido_tarj", 0]},
                                0,
                            ]
                        }
                    },
                    "tarjeta_credito": {
                        "$sum": {
                            "$cond": [
                                {"$eq": ["$tipo_tarjeta", "credito"]},
                                {"$ifNull": ["$recibido_tarj", 0]},
                                0,
                            ]
                        }
                    },
                    "transferencia": {"$sum": {"$ifNull": ["$recibido_trans", 0]}},
                    "total_general": {"$sum": "$recibido_total"},
                }
            },
        ]

        resultado = list(db_client.pbstation.ventas.aggregate(pipeline))

        if resultado:
            r = resultado[0]
            total = _decimal128_to_float(r["total_general"])
            
            def pct(val):
                v = _decimal128_to_float(val)
                return round((v / total * 100) if total > 0 else 0, 1)

            metodos = [
                {"tipo": "Efectivo MXN", "total": round(_decimal128_to_float(r["efectivo_mxn"]), 2), "porcentaje": pct(r["efectivo_mxn"])},
                {"tipo": "Efectivo USD", "total": round(_decimal128_to_float(r["efectivo_us"]), 2), "porcentaje": pct(r["efectivo_us"])},
                {"tipo": "Tarjeta Débito", "total": round(_decimal128_to_float(r["tarjeta_debito"]), 2), "porcentaje": pct(r["tarjeta_debito"])},
                {"tipo": "Tarjeta Crédito", "total": round(_decimal128_to_float(r["tarjeta_credito"]), 2), "porcentaje": pct(r["tarjeta_credito"])},
                {"tipo": "Transferencia", "total": round(_decimal128_to_float(r["transferencia"]), 2), "porcentaje": pct(r["transferencia"])},
            ]
            return {"metodos": metodos, "total_general": round(total, 2)}
        
        return {"metodos": [], "total_general": 0}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener métodos de pago: {str(e)}",
        )


# ─────────────────────────── POR SUCURSAL ──────────────────────────────
@router.get("/por-sucursal")
async def obtener_por_sucursal(
    periodo: str = Query("mes", regex="^(semana|mes|todo|custom)$"),
    fecha_inicio: str = None,
    fecha_fin: str = None,
    token: dict = Depends(require_permission("elevado")),
):
    try:
        match = {
            "liquidado": True,
            "cancelado": {"$ne": True},
            "was_deuda": {"$ne": True},
        }
        filtro_fecha = _filtro_periodo(periodo, fecha_inicio, fecha_fin)
        match.update(filtro_fecha)

        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": "$sucursal_id",
                    "total": {"$sum": "$total"},
                    "num_ventas": {"$sum": 1},
                    "ticket_promedio": {"$avg": "$total"},
                }
            },
            {"$sort": {"total": -1}},
        ]

        resultado = list(db_client.pbstation.ventas.aggregate(pipeline))

        sucursales_ids = [r["_id"] for r in resultado if r["_id"]]
        sucursales_map = {}
        if sucursales_ids:
            sucursales_cursor = db_client.pbstation.sucursales.find(
                {"_id": {"$in": [ObjectId(sid) for sid in sucursales_ids]}},
                {"nombre": 1}
            )
            sucursales_map = {str(s["_id"]): s.get("nombre", "Sin nombre") for s in sucursales_cursor}

        sucursales = []
        for r in resultado:
            sucursal_id = r["_id"]
            sucursales.append({
                "sucursal_id": sucursal_id,
                "nombre": sucursales_map.get(sucursal_id, "Sucursal eliminada"),
                "total": round(_decimal128_to_float(r["total"]), 2),
                "num_ventas": r["num_ventas"],
                "ticket_promedio": round(_decimal128_to_float(r["ticket_promedio"]), 2),
            })

        return sucursales

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener reporte por sucursal: {str(e)}",
        )


# ─────────────────────────── CANCELACIONES ─────────────────────────────
@router.get("/cancelaciones")
async def obtener_cancelaciones(
    periodo: str = Query("mes", regex="^(semana|mes|todo|custom)$"),
    fecha_inicio: str = None,
    fecha_fin: str = None,
    sucursal_id: str = None,
    token: dict = Depends(require_permission("elevado")),
):
    try:
        match = {"cancelado": True}
        filtro_fecha = _filtro_periodo(periodo, fecha_inicio, fecha_fin)
        match.update(filtro_fecha)
        if sucursal_id:
            match["sucursal_id"] = sucursal_id

        pipeline_totales = [
            {"$match": match},
            {
                "$group": {
                    "_id": None,
                    "total_cancelado": {"$sum": "$total"},
                    "num_cancelaciones": {"$sum": 1},
                }
            },
        ]

        pipeline_motivos = [
            {"$match": match},
            {
                "$group": {
                    "_id": {"$ifNull": ["$motivo_cancelacion", "Sin motivo"]},
                    "cantidad": {"$sum": 1},
                    "monto": {"$sum": "$total"},
                }
            },
            {"$sort": {"cantidad": -1}},
            {"$limit": 10},
        ]

        resultado_totales = list(db_client.pbstation.ventas.aggregate(pipeline_totales))
        resultado_motivos = list(db_client.pbstation.ventas.aggregate(pipeline_motivos))

        total_cancelado = _decimal128_to_float(resultado_totales[0]["total_cancelado"]) if resultado_totales else 0
        num_cancelaciones = resultado_totales[0]["num_cancelaciones"] if resultado_totales else 0

        motivos = []
        for r in resultado_motivos:
            motivos.append({
                "motivo": r["_id"],
                "cantidad": r["cantidad"],
                "monto": round(_decimal128_to_float(r["monto"]), 2),
            })

        return {
            "total_cancelado": round(total_cancelado, 2),
            "num_cancelaciones": num_cancelaciones,
            "motivos": motivos,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener cancelaciones: {str(e)}",
        )


# ─────────────────────────── TENDENCIAS ────────────────────────────────
@router.get("/tendencias")
async def obtener_tendencias(
    periodo: str = Query("mes", regex="^(semana|mes|todo|custom)$"),
    fecha_inicio: str = None,
    fecha_fin: str = None,
    sucursal_id: str = None,
    token: dict = Depends(require_permission("elevado")),
):
    try:
        match = _base_match(periodo, sucursal_id, fecha_inicio, fecha_fin)
        match["was_deuda"] = {"$ne": True}

        pipeline_horas = [
            {"$match": match},
            {
                "$group": {
                    "_id": {"$hour": "$fecha_venta"},
                    "total": {"$sum": "$total"},
                    "num_ventas": {"$sum": 1},
                }
            },
            {"$sort": {"_id": 1}},
        ]

        pipeline_dias = [
            {"$match": match},
            {
                "$group": {
                    "_id": {"$dayOfWeek": "$fecha_venta"},
                    "total": {"$sum": "$total"},
                    "num_ventas": {"$sum": 1},
                }
            },
            {"$sort": {"_id": 1}},
        ]

        pipeline_serie = [
            {"$match": match},
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$fecha_venta",
                        }
                    },
                    "total": {"$sum": "$total"},
                    "num_ventas": {"$sum": 1},
                }
            },
            {"$sort": {"_id": 1}},
        ]

        resultado_horas = list(db_client.pbstation.ventas.aggregate(pipeline_horas))
        resultado_dias = list(db_client.pbstation.ventas.aggregate(pipeline_dias))
        resultado_serie = list(db_client.pbstation.ventas.aggregate(pipeline_serie))

        dias_semana_map = {1: "Domingo", 2: "Lunes", 3: "Martes", 4: "Miércoles", 5: "Jueves", 6: "Viernes", 7: "Sábado"}

        por_hora = []
        for r in resultado_horas:
            por_hora.append({
                "hora": r["_id"],
                "total": round(_decimal128_to_float(r["total"]), 2),
                "num_ventas": r["num_ventas"],
            })

        por_dia = []
        for r in resultado_dias:
            por_dia.append({
                "dia_semana": r["_id"],
                "dia_nombre": dias_semana_map.get(r["_id"], "?"),
                "total": round(_decimal128_to_float(r["total"]), 2),
                "num_ventas": r["num_ventas"],
            })

        serie_diaria = []
        for r in resultado_serie:
            serie_diaria.append({
                "fecha": r["_id"],
                "total": round(_decimal128_to_float(r["total"]), 2),
                "num_ventas": r["num_ventas"],
            })

        return {
            "por_hora": por_hora,
            "por_dia": por_dia,
            "serie_diaria": serie_diaria,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener tendencias: {str(e)}",
        )
