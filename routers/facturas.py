import base64
from typing import Optional
from bson import Decimal128
from fastapi import APIRouter, HTTPException, Response, status, Depends, Header
import requests
from os import getenv
from core.database import db_client
from models.factura import Factura
from schemas.factura import factura_schema, facturas_schema
from validar_token import validar_token
from routers.websocket import manager 

router = APIRouter(prefix="/facturacion", tags=["Facturación"])

FACTURAMA_USER = getenv("FACTURAMA_USER")
FACTURAMA_PASS = getenv("FACTURAMA_PASS")
BASE_URL = "https://apisandbox.facturama.mx"

@router.get("/all")
async def obtener_facturas(
    page: int = 1,
    page_size: int = 60,
    rfc: Optional[str] = None,
    sucursal_id: Optional[str] = None,
    token: str = Depends(validar_token)
):
    filtros = {}
    
    # Filtrar por RFC (búsqueda parcial, case-insensitive)
    if rfc:
        filtros["receptor_rfc"] = {"$regex": rfc, "$options": "i"}
    
    # Filtrar por sucursal
    if sucursal_id:
        filtros["sucursal_id"] = sucursal_id
    
    total = db_client.local.facturas.count_documents(filtros)
    skip = (page - 1) * page_size
    facturas = db_client.local.facturas.find(filtros)\
        .sort("fecha_creacion", -1)\
        .skip(skip)\
        .limit(page_size)
    total_pages = (total + page_size - 1) // page_size
    return {
        "data": facturas_schema(facturas),
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }

@router.post("/", response_model=Factura, status_code=status.HTTP_201_CREATED) #post
async def crear_factura(factura: Factura, token: str = Depends(validar_token), x_connection_id: Optional[str] = Header(None)):
    # TODO: validar que no exista una factura de la venta_id

    factura_dict = dict(factura)
    del factura_dict["id"] #quitar el id para que no se guarde como null
    factura_dict["subtotal"] = Decimal128(factura_dict["subtotal"])
    factura_dict["descuento"] = Decimal128(factura_dict["descuento"])
    factura_dict["impuestos"] = Decimal128(factura_dict["impuestos"])
    factura_dict["total"] = Decimal128(factura_dict["total"])

    id = db_client.local.facturas.insert_one(factura_dict).inserted_id #mongodb crea automaticamente el id como "_id"
    
    nueva_factura = factura_schema(db_client.local.facturas.find_one({"_id":id}))

    await manager.broadcast(
        f"post-factura:{str(id)}",
        exclude_connection_id=x_connection_id
    )
    return Factura(**nueva_factura) #el ** sirve para pasar los valores del diccionario


@router.get("/check")
def check():
    endpoint = f"{BASE_URL}/api/Catalogs/States"
    r = requests.get(endpoint, auth=(FACTURAMA_USER, FACTURAMA_PASS))
    return r.json()

@router.post("/crear")
def crear_factura(cfdi: dict):
    url = f"{BASE_URL}/3/cfdis"
    r = requests.post(url, json=cfdi, auth=(FACTURAMA_USER, FACTURAMA_PASS))
    return r.json()

@router.get("/pdf/{id}")
def descargar_pdf(id: str):
    url = f"{BASE_URL}/api/cfdi/pdf/{id}"
    r = requests.get(url, auth=(FACTURAMA_USER, FACTURAMA_PASS))

    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=f"Error de Facturama: {r.text}")
    
    try:
        data = r.json()
        if "Content" not in data:
            raise HTTPException(status_code=500, detail=f"Respuesta inesperada de Facturama: {data}")
        pdf_base64 = data["Content"]
        pdf_bytes = base64.b64decode(pdf_base64)
        return Response(content=pdf_bytes, media_type="application/pdf")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando PDF: {str(e)}")

@router.get("/xml/{id}")
def descargar_xml(id: str):
    url = f"{BASE_URL}/api/cfdi/xml/{id}"
    r = requests.get(url, auth=(FACTURAMA_USER, FACTURAMA_PASS))

    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=f"Error de Facturama: {r.text}")
    
    try:
        data = r.json()
        if "Content" not in data:
            raise HTTPException(status_code=500, detail=f"Respuesta inesperada de Facturama: {data}")
        xml_base64 = data["Content"]
        xml_bytes = base64.b64decode(xml_base64)
        return Response(content=xml_bytes, media_type="application/xml")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando XML: {str(e)}")