# schemas/correo.py
from pydantic import BaseModel, EmailStr
from typing import List

class EmailSchema(BaseModel):
    email: List[EmailStr] # Lista de destinatarios
    body: str             # Cuerpo del mensaje
    subject: str          # Asunto del correo
