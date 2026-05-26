# schemas/correo.py
from pydantic import BaseModel, EmailStr
from typing import List, Optional

class EmailSchema(BaseModel):
    email: List[EmailStr] # Lista de destinatarios
    body: str             # Cuerpo del mensaje
    subject: str          # Asunto del correo
    attachment_base64: Optional[str] = None # Adjunto en base64
    attachment_name: Optional[str] = None # Nombre del archivo adjunto
