from core.database import db

def cargar_config():
    config = db.configuracion.find_one({}, {"_id": 0})
    if config is None:
        config = {
            "precio_dolar": 0,
            "iva": 0,
            "last_version": "1.0.0"
        }
        db.configuracion.insert_one(config)
        config.pop("_id", None)
    return config

def guardar_config(data: dict):
    data.pop("_id", None)
    db.configuracion.replace_one({}, data, upsert=True)