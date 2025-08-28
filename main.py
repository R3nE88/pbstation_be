from fastapi import FastAPI
from routers import configuracion, productos, usuarios, login, websocket, clientes, ventas, sucursales, cotizaciones, ventas_enviadas, cajas, impresoras, contadores
from fastapi.staticfiles import StaticFiles
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


iniciar_scheduler()

#app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/helloworld")
async def helloworld():
    return {"Hello Word": "how are you"}





#URL local: http://127.0.0.1:8000
#Inicia el server: uvicorn main:app --reload
# Documentacion con Swagger: /docs
# Iniciar venv: venv\Scripts\activate