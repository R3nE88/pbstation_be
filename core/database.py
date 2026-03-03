from pymongo import MongoClient

db_client = MongoClient() #en localhost no necesita mucha configuracion
db = db_client.pbstation