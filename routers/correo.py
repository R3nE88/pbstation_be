# routers/correo.py
from fastapi import APIRouter, BackgroundTasks, Depends
from core.mail import enviar_correo_base
from schemas.correo import EmailSchema
from validar_token import validar_token

router = APIRouter(
    prefix="/correo",
    tags=["Correo"]
)

@router.post("/enviar")
async def enviar_correo(
    email_data: EmailSchema, 
    background_tasks: BackgroundTasks,
    token: str = Depends(validar_token)
):
    # Se utiliza BackgroundTasks para que la API no se quede esperando a que el correo termine de enviarse
    background_tasks.add_task(enviar_correo_base, email_data)
    
    return {"mensaje": f"Correo en proceso de enviarse a {email_data.email}"}
