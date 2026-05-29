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

class DatosEmisorUpdate(BaseModel):
    empresa: str = Field(..., description="Nombre de la empresa")
    ciudad: str = Field(..., description="Ciudad de la empresa")
    nombre_emisor: str = Field(..., description="Nombre del emisor")
    direccion_emisor: str = Field(..., description="Dirección del emisor")
    telefono_emisor: str = Field(..., description="Teléfono del emisor")
    rfc_emisor: str = Field(..., description="RFC del emisor")

class CredencialesCorreoUpdate(BaseModel):
    mail_username: str = Field(...)
    mail_password: str = Field(...)
    mail_from: str = Field(...)
    mail_port: int = Field(...)
    mail_server: str = Field(...)

class CredencialesFacturamaUpdate(BaseModel):
    facturama_user: str = Field(...)
    facturama_pass: str = Field(...)

@router.get("/")
def obtener_config():
    config = cargar_config()
    # Enmascarar contraseñas para el endpoint público
    config["mail_password"] = "********" if config.get("mail_password") else ""
    config["facturama_pass"] = "********" if config.get("facturama_pass") else ""
    return config

@router.get("/admin")
def obtener_config_admin(token: dict = Depends(require_permission("admin"))):
    return cargar_config()

@router.put("/precio-dolar")
async def actualizar_precio_dolar(
    data: PrecioDolarUpdate,
    token: dict = Depends(require_permission("elevado")),
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
    token: dict = Depends(require_permission("elevado")),
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

@router.put("/datos-emisor")
async def actualizar_datos_emisor(
    data: DatosEmisorUpdate,
    token: dict = Depends(require_permission("elevado")),
    x_connection_id: Optional[str] = Header(None)
):
    config = cargar_config()
    config["empresa"] = data.empresa
    config["ciudad"] = data.ciudad
    config["nombre_emisor"] = data.nombre_emisor
    config["direccion_emisor"] = data.direccion_emisor
    config["telefono_emisor"] = data.telefono_emisor
    config["rfc_emisor"] = data.rfc_emisor
    guardar_config(config)

    await manager.broadcast(
        "put-configuracion",
        exclude_connection_id=x_connection_id
    )

    return {
        "message": "Datos de emisor actualizados correctamente"
    }

@router.put("/credenciales-correo")
async def actualizar_credenciales_correo(
    data: CredencialesCorreoUpdate,
    token: dict = Depends(require_permission("admin")),
    x_connection_id: Optional[str] = Header(None)
):
    config = cargar_config()
    config["mail_username"] = data.mail_username
    
    # Solo actualizar el password si no es la máscara
    if data.mail_password != "********":
        config["mail_password"] = data.mail_password
        
    config["mail_from"] = data.mail_from
    config["mail_port"] = data.mail_port
    config["mail_server"] = data.mail_server
    guardar_config(config)

    await manager.broadcast(
        "put-configuracion",
        exclude_connection_id=x_connection_id
    )

    return {"message": "Credenciales de correo actualizadas"}

@router.put("/credenciales-facturama")
async def actualizar_credenciales_facturama(
    data: CredencialesFacturamaUpdate,
    token: dict = Depends(require_permission("admin")),
    x_connection_id: Optional[str] = Header(None)
):
    config = cargar_config()
    config["facturama_user"] = data.facturama_user
    
    # Solo actualizar el password si no es la máscara
    if data.facturama_pass != "********":
        config["facturama_pass"] = data.facturama_pass
        
    guardar_config(config)

    await manager.broadcast(
        "put-configuracion",
        exclude_connection_id=x_connection_id
    )

    return {"message": "Credenciales de Facturama actualizadas"}
