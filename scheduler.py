from apscheduler.schedulers.background import BackgroundScheduler
from core.database import db_client
from datetime import datetime
from pytz import timezone

# Conexión a tu base de datos MongoDB
db = db_client.local

def verificar_cotizaciones_vencidas():
    print("Verificando cotizaciones vencidas...")
    zona = timezone("America/Hermosillo")
    print("Hora local:", datetime.now(zona))
    hoy = datetime.now()
    cotizaciones = db.cotizaciones.find({"vigente": True})

    vencidas = []
    for c in cotizaciones:
        fecha = datetime.strptime(c["fecha_cotizacion"], "%Y-%m-%d %H:%M:%S.%f")
        if fecha.month < hoy.month or fecha.year < hoy.year:
            vencidas.append(c["_id"])

    if vencidas:
        db.cotizaciones.update_many(
            {"_id": {"$in": vencidas}},
            {"$set": {"vigente": False}}
        )
        print(f"Actualizadas {len(vencidas)} cotizaciones como vencidas")

def iniciar_scheduler():
    verificar_cotizaciones_vencidas()
    scheduler = BackgroundScheduler(timezone="America/Hermosillo")
    scheduler.add_job(verificar_cotizaciones_vencidas, 'cron', hour=16, minute=0)  # cada día a las 2am
    scheduler.start()
