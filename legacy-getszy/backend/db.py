import os
from motor.motor_asyncio import AsyncIOMotorClient

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'getszy_db')]


def serialize_doc(doc):
    """Remove Mongo _id and ensure JSON serializable."""
    if doc is None:
        return None
    doc = {k: v for k, v in doc.items() if k != '_id'}
    return doc
