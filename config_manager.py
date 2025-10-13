import json
from pathlib import Path

CONFIG_PATH = Path("configuracion.json")

def cargar_config():
    if not CONFIG_PATH.exists():
        guardar_config({
            "precio_dolar": 0,
            "iva": 0,
            "last_version": "1.0.0"  # Valor por defecto
        })
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_config(data: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)