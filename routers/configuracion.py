import os
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Header, status
from fastapi.params import Depends
from pydantic import BaseModel, Field
from config_manager import cargar_config, guardar_config
from routers.websocket import manager 

# Cargar variables de entorno desde config.env
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.env")
load_dotenv(dotenv_path=dotenv_path)

SECRET_KEY = os.getenv("SECRET_KEY")
SECRET_KEY = SECRET_KEY.strip()  # Eliminar espacios o saltos de línea

def validar_token(tkn: str = Header(None, description="El token de autorización es obligatorio")):
    if tkn is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sin Authorizacion"
        )
    if tkn != SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorizacion inválida"
        )

router = APIRouter(prefix="/configuracion", tags=["configuracion"])

class ConfigUpdate(BaseModel):
    precio_dolar: float = Field(..., gt=0, description="Precio actual del dólar")
    iva: int = Field(..., ge=0, le=100, description="Porcentaje de IVA")

@router.get("/")
def obtener_config(token: str = Depends(validar_token)):
    return cargar_config()

@router.put("/")
async def actualizar_config(config: ConfigUpdate, token: str = Depends(validar_token)):
    guardar_config(config.model_dump())

    await manager.broadcast(f"put-configuracion") #Notificar a todos

    return {
        "message": "Configuración actualizada correctamente",
        "nueva_configuracion": config.model_dump()
    }