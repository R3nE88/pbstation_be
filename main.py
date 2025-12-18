from fastapi import FastAPI
from routers import configuracion, productos, usuarios, login, websocket, clientes, ventas, sucursales, cotizaciones, ventas_enviadas, cajas, impresoras, contadores, pedidos
from scheduler import iniciar_scheduler
app = FastAPI()

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

iniciar_scheduler()

@app.get("/helloworld")
async def helloworld():
    return {"Hello Word": "how are you"}

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