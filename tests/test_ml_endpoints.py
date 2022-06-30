import requests, random
from dotenv import load_dotenv
import os, pymongo, time

load_dotenv()

def get_mongo_handle():
    db_name = os.environ.get('MONGO_DB_NAME', None)
    CONNECTION_STRING = os.environ.get("MONGO_CONNECTION_STRING", None)
    client = pymongo.MongoClient(CONNECTION_STRING)
    return client[db_name] 
    
HOSTNAME = os.environ.get("SERVER_ENDPOINT", None)
db = get_mongo_handle()

#remove saved models so we can see first time response
db['ml'].delete_many({})
print("Deleted all items from ml collection")

#reset update time
print("Resetting update time")
db['config'].update_one({"key": "last_model_update_time"}, { "$set": { 'value': None} }) 

PUBLISH_PASSWORD = os.environ.get("PUBLISH_PASSWORD")
URL = f"{HOSTNAME}/sensor_data/publish?password={PUBLISH_PASSWORD}"
print(URL)


print("Testing endpoints")

#change mode
db['config'].update_one({"key": "mode"}, { "$set": { 'value': "machine_learning"} }) #enter ML mode

data = {
    "baro_pressure": random.randrange(100),
    "ext_temp":  random.randrange(100),
    "humidity":  random.randrange(100),
    "wind_speed":  random.randrange(100),
    "wind_direction":  random.choice(['N', 'W', 'S', 'E']),
    "internal_temp": random.randrange(60),
    "uv": random.randrange(10),
    "battery_percentage": random.randrange(100),
    "gas_resistance" : random.randrange(50000),
    "precipitation_mmhr": random.randrange(500)*0.2974,
}

print("Posting data in ML mode. This will send a request to train the model.")
r = requests.post(url=URL, json=data)
print(r) 

time.sleep(3*60) #best not to rush it

print("Fetch new model.")
r = requests.post(url=URL, json=data)
print(r) 
endpoints = [
    ["/ml_img", "Get current ml image", "get"],
    ["/ml_info", "Get current ml info", "get"],
    ["/get_training_freq", "Getting training frequency", "get"],
    ["/set_training_freq/30", "Setting training frequency to 30 days", "post"],
    ["/get_training_freq", "Getting training freq again to see changes", "get" ],
    ["/set_training_freq/21", "Resetting training frequency", "post"],
]

for endpoint, message, method in endpoints:

    #deal with error messages from request
    print(message)
    url = HOSTNAME + endpoint
    print(url)
    if method == "post":
        print(requests.post(url=url))
    else:
        print(requests.get(url=url))

    print("\n")

print("Tests done")
db['config'].update_one({"key": "mode"}, { "$set": { 'value': "weather_api"} }) #back to weather mode
