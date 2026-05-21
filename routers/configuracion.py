import os
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, status
from fastapi.params import Depends
from pydantic import BaseModel, Field
from config_manager import cargar_config, guardar_config
from routers.websocket import manager
from validar_token import require_permission, validar_token

router = APIRouter(prefix="/configuracion", tags=["configuracion"])

class PrecioDolarUpdate(BaseModel):
    precio_dolar: float = Field(..., gt=0, description="Precio actual del dólar")

class IvaUpdate(BaseModel):
    iva: int = Field(..., ge=0, le=100, description="Porcentaje de IVA")

class VersionUpdate(BaseModel):
    last_version: str = Field(..., description="Versión actual del sistema")

@router.get("/")
def obtener_config():
    return cargar_config()

@router.put("/precio-dolar")
async def actualizar_precio_dolar(
    data: PrecioDolarUpdate,
    token: dict = Depends(require_permission("admin")),
    x_connection_id: Optional[str] = Header(None)
):
    config = cargar_config()
    config["precio_dolar"] = data.precio_dolar
    guardar_config(config)

    await manager.broadcast(
        "put-configuracion",
        exclude_connection_id=x_connection_id
    )

    return {
        "message": "Precio del dólar actualizado correctamente",
        "precio_dolar": data.precio_dolar
    }

@router.put("/iva")
async def actualizar_iva(
    data: IvaUpdate,
    token: dict = Depends(require_permission("admin")),
    x_connection_id: Optional[str] = Header(None)
):
    config = cargar_config()
    config["iva"] = data.iva
    guardar_config(config)

    await manager.broadcast(
        "put-configuracion",
        exclude_connection_id=x_connection_id
    )

    return {
        "message": "IVA actualizado correctamente",
        "iva": data.iva
    }

@router.put("/version")
async def actualizar_version(
    data: VersionUpdate,
    token: dict = Depends(require_permission("admin")),
    x_connection_id: Optional[str] = Header(None)
):
    config = cargar_config()
    config["last_version"] = data.last_version
    guardar_config(config)

    await manager.broadcast(
        "put-configuracion",
        exclude_connection_id=x_connection_id
    )

    return {
        "message": "Versión actualizada correctamente",
        "last_version": data.last_version
    }

