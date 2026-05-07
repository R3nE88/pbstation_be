from apscheduler.schedulers.asyncio import AsyncIOScheduler
from core.database import db_client
from datetime import datetime
from pytz import timezone
from routers.websocket import manager

# Conexión a tu base de datos MongoDB
db = db_client.pbstation

async def verificar_cotizaciones_vencidas():
    print("Verificando cotizaciones vencidas...")
    zona = timezone("America/Hermosillo")
    print("Hora local:", datetime.now(zona))
    hoy = datetime.now()
    # Primer día del mes actual — cotizaciones de meses anteriores están vencidas
    inicio_mes = datetime(hoy.year, hoy.month, 1)
    cotizaciones = db.cotizaciones.find({"vigente": True})

    vencidas = []
    for c in cotizaciones:
        fecha = c["fecha_cotizacion"]
        if fecha < inicio_mes:
            vencidas.append(c["_id"])

    if vencidas:
        db.cotizaciones.update_many(
            {"_id": {"$in": vencidas}},
            {"$set": {"vigente": False}}
        )
        await manager.broadcast("reload-cotizaciones")
        print(f"Actualizadas {len(vencidas)} cotizaciones como vencidas")

def iniciar_scheduler():
    scheduler = AsyncIOScheduler(timezone="America/Hermosillo")
    scheduler.add_job(
        verificar_cotizaciones_vencidas, 
        'cron', 
        hour=10, 
        minute=0,
        misfire_grace_time=None
    )  # cada día a las 2am, misfire_grace_time evita que se cancele si la PC estaba suspendida
    scheduler.start()

