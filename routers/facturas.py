import base64
from typing import Optional
from bson import Decimal128
from fastapi import APIRouter, HTTPException, status, Depends, Header
import requests
from core.database import db_client
from models.factura import Factura
from schemas.factura import factura_schema
from validar_token import validar_token
from routers.websocket import manager 

router = APIRouter(prefix="/facturacion", tags=["Facturación"])

FACTURAMA_USER = "printerboy"
FACTURAMA_PASS = "DIOE860426"

BASE_URL = "https://apisandbox.facturama.mx"

@router.post("/", response_model=Factura, status_code=status.HTTP_201_CREATED) #post
async def crear_factura(factura: Factura, token: str = Depends(validar_token), x_connection_id: Optional[str] = Header(None)):
    # TODO: validar que no exista una factura de la venta_id

    factura_dict = dict(factura)
    del factura_dict["id"] #quitar el id para que no se guarde como null
    factura_dict["subtotal"] = Decimal128(factura_dict["subtotal"])
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

    data = r.json()
    pdf_base64 = data["Content"]
    pdf_bytes = base64.b64decode(pdf_base64)

    return Response(content=pdf_bytes, media_type="application/pdf")

@router.get("/xml/{id}")
def descargar_xml(id: str):
    url = f"{BASE_URL}/api/cfdi/xml/{id}"
    r = requests.get(url, auth=(FACTURAMA_USER, FACTURAMA_PASS))

    data = r.json()
    xml_base64 = data["Content"]
    xml_bytes = base64.b64decode(xml_base64)

    return Response(content=xml_bytes, media_type="application/xml")