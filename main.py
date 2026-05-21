from fastapi import FastAPI
from dotenv import load_dotenv
import os
import routers.facturas as facturas
from routers import configuracion, productos, usuarios, login, websocket, clientes, ventas, sucursales, cotizaciones, ventas_enviadas, cajas, impresoras, contadores, pedidos, correo
from scheduler import iniciar_scheduler, verificar_cotizaciones_vencidas
from init_database import crear_configuracion_defecto, crear_usuario_admin_defecto, crear_cliente_defecto, crear_indices_auth
from schemas.usuario import usuario_public_schema
from validar_token import revocar_sesion, validar_token
from fastapi import Depends

load_dotenv()

debug = os.getenv("DEBUG")
if debug == "true":
    app = FastAPI()
else:
    app = FastAPI(
        docs_url=None,
        redoc_url=None,
        openapi_url=None
    )

# Inicializar base de datos con datos por defecto
crear_configuracion_defecto()
crear_usuario_admin_defecto()
crear_cliente_defecto()
crear_indices_auth()

#Routers
app.include_router(login.router)
app.include_router(websocket.router)
app.include_router(usuarios.router)
app.include_router(clientes.router)
app.include_router(productos.router)
app.include_router(configuracion.router)
app.include_router(ventas.router)
app.include_router(ventas_enviadas.router)
app.include_router(sucursales.router)
app.include_router(cajas.router)
app.include_router(cotizaciones.router)
app.include_router(impresoras.router)
app.include_router(contadores.router)
app.include_router(pedidos.router)
app.include_router(facturas.router)
app.include_router(correo.router)

@app.on_event("startup")
async def startup_event():
    iniciar_scheduler()
    await verificar_cotizaciones_vencidas()

@app.get("/helloworld")
async def helloworld():
    return {"Hello Word": "how are you"}

@app.get("/me")
async def me(usuario: dict = Depends(validar_token)):
    return usuario_public_schema(usuario)

@app.post("/logout")
async def logout(usuario: dict = Depends(validar_token)):
    revocar_sesion(usuario["session_id"])
    return {"message": "Sesion cerrada"}

#URL local: http://127.0.0.1:8000
#Inicia el server: uvicorn main:app --reload
# Documentacion con Swagger: /docs
# Iniciar venv: venv\Scripts\activate
# hola desde nueva pc 


### Ejemplo cliente (publico general)
# {
#   "nombre": "Publico General",
#   "correo": null,
#   "telefono": null,
#   "razon_social": null,
#   "rfc": "XAXX010101000 ",
#   "regimen_fiscal": "616",
#   "codigo_postal": null,
#   "direccion": null,
#   "no_ext": null,
#   "no_int": null,
#   "colonia": null,
#   "localidad": null,
#   "adeudos": [
#   ],
#   "protegido": true,
#   "activo": true
# }
