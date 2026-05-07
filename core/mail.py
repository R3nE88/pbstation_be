# core/mail.py
import os
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from dotenv import load_dotenv
from typing import List
from schemas.correo import EmailSchema

load_dotenv()

# Instanciar la configuración usando las variables de entorno
conf = ConnectionConfig(
    MAIL_USERNAME = os.getenv('MAIL_USERNAME'),
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD'),
    MAIL_FROM = os.getenv('MAIL_FROM'),
    MAIL_PORT = int(os.getenv('MAIL_PORT', 465)),
    MAIL_SERVER = os.getenv('MAIL_SERVER'),
    MAIL_STARTTLS = False,
    MAIL_SSL_TLS = True,
    USE_CREDENTIALS = True,
    VALIDATE_CERTS = True
)

async def enviar_correo_base(email_data: EmailSchema):
    """Función de utilidad para enviar correos fácilmente"""
    message = MessageSchema(
        subject=email_data.subject,
        recipients=email_data.email,
        body=email_data.body,
        subtype=MessageType.html # Cambia a MessageType.plain si no usas HTML
    )

    fm = FastMail(conf)
    await fm.send_message(message)
