import os
from pymongo import MongoClient

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
db_client = MongoClient(MONGODB_URL)
db = db_client.pbstation