from fastapi import FastAPI
from routers import productos, usuarios, login, websocket
from fastapi.staticfiles import StaticFiles

app = FastAPI()


#Routers
app.include_router(usuarios.router)
app.include_router(login.router)
app.include_router(productos.router)
app.include_router(websocket.router)
#app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/helloworld")
async def helloworld():
    return {"Hello Word": "how are you"}

#URL local: http://127.0.0.1:8000
#Inicia el server: uvicorn main:app --reload
# Documentacion con Swagger: /docs
# Iniciar venv: venv\Scripts\activate