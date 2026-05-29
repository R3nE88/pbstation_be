from core.database import db
import os

def cargar_config():
    config = db.configuracion.find_one({}, {"_id": 0})
    if config is None:
        config = {
            "precio_dolar": 0,
            "iva": 0,
            "last_version": "1.0.0",
            "empresa": "",
            "ciudad": "",
            "nombre_emisor": "",
            "direccion_emisor": "",
            "telefono_emisor": "",
            "rfc_emisor": "",
            "mail_username": os.getenv("MAIL_USERNAME", ""),
            "mail_password": os.getenv("MAIL_PASSWORD", ""),
            "mail_from": os.getenv("MAIL_FROM", ""),
            "mail_port": int(os.getenv("MAIL_PORT", 465)),
            "mail_server": os.getenv("MAIL_SERVER", ""),
            "facturama_user": os.getenv("FACTURAMA_USER", ""),
            "facturama_pass": os.getenv("FACTURAMA_PASS", "")
        }
        db.configuracion.insert_one(config)
        config.pop("_id", None)
    else:
        # Migración: asegurar que las nuevas llaves existan
        needs_update = False
        default_keys = {
            "mail_username": os.getenv("MAIL_USERNAME", ""),
            "mail_password": os.getenv("MAIL_PASSWORD", ""),
            "mail_from": os.getenv("MAIL_FROM", ""),
            "mail_port": int(os.getenv("MAIL_PORT", 465)),
            "mail_server": os.getenv("MAIL_SERVER", ""),
            "facturama_user": os.getenv("FACTURAMA_USER", ""),
            "facturama_pass": os.getenv("FACTURAMA_PASS", "")
        }
        for k, v in default_keys.items():
            if k not in config:
                config[k] = v
                needs_update = True
        
        if needs_update:
            guardar_config(config.copy())
            
    return config

def guardar_config(data: dict):
    data.pop("_id", None)
    db.configuracion.replace_one({}, data, upsert=True)