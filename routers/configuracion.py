import os
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, status
from fastapi.params import Depends
from pydantic import BaseModel, Field
from config_manager import cargar_config, guardar_config
from routers.websocket import manager
from validar_token import validar_token 

router = APIRouter(prefix="/configuracion", tags=["configuracion"])

class ConfigUpdate(BaseModel):
    precio_dolar: float = Field(..., gt=0, description="Precio actual del dólar")
    iva: int = Field(..., ge=0, le=100, description="Porcentaje de IVA")

@router.get("/")
def obtener_config(token: str = Depends(validar_token)):
    return cargar_config()

@router.put("/")
async def actualizar_config(config: ConfigUpdate, token: str = Depends(validar_token), x_connection_id: Optional[str] = Header(None)):
    guardar_config(config.model_dump())

    await manager.broadcast(
        f"put-configuracion:{str(id)}", 
        exclude_connection_id=x_connection_id
    )

    return {
        "message": "Configuración actualizada correctamente",
        "nueva_configuracion": config.model_dump()
    }