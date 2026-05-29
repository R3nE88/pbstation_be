# core/mail.py
import os
import base64
import tempfile
import shutil
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from dotenv import load_dotenv
from typing import List
from schemas.correo import EmailSchema

load_dotenv()

from config_manager import cargar_config

async def enviar_correo_base(email_data: EmailSchema):
    """Función de utilidad para enviar correos fácilmente"""
    attachments = []
    temp_dir = None
    
    if email_data.attachment_base64 and email_data.attachment_name:
        file_bytes = base64.b64decode(email_data.attachment_base64)
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, email_data.attachment_name)
        with open(temp_file_path, "wb") as f:
            f.write(file_bytes)
        attachments.append(temp_file_path)

    message = MessageSchema(
        subject=email_data.subject,
        recipients=email_data.email,
        body=email_data.body,
        subtype=MessageType.html, # Cambia a MessageType.plain si no usas HTML
        attachments=attachments if attachments else None
    )

    config = cargar_config()
    conf = ConnectionConfig(
        MAIL_USERNAME = config.get("mail_username", ""),
        MAIL_PASSWORD = config.get("mail_password", ""),
        MAIL_FROM = config.get("mail_from", ""),
        MAIL_PORT = int(config.get("mail_port", 465)),
        MAIL_SERVER = config.get("mail_server", ""),
        MAIL_STARTTLS = False,
        MAIL_SSL_TLS = True,
        USE_CREDENTIALS = True,
        VALIDATE_CERTS = True
    )

    fm = FastMail(conf)
    try:
        await fm.send_message(message)
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
