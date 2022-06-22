import os, pymongo
from dotenv import load_dotenv
import datetime

load_dotenv()

def get_mongo_handle():
    db_name = os.environ.get('MONGO_DB_NAME', None)
    CONNECTION_STRING = os.environ.get("MONGO_CONNECTION_STRING", None)
    client = pymongo.MongoClient(CONNECTION_STRING)
    return client[db_name] 

print("Testing Database")
db = get_mongo_handle()
db["hey"].insert_one({ "key": "test", "value": "value" })
assert db['hey'].find_one({"key": "test"})["value"] == "value"
print("Inserted successfully")
db["hey"].delete_one({"key":"test"})
print("Done! Tests passed.")