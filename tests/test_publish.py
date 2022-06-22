import requests, random, os
from dotenv import load_dotenv

load_dotenv()

HOSTNAME = "http://127.0.0.1:5000"
PUBLISH_PASSWORD = os.environ.get("PUBLISH_PASSWORD")
URL = f"{HOSTNAME}/sensor_data/publish?password={PUBLISH_PASSWORD}"
print(URL)


print("Testing publish")
data = {
    "baro_pressure": random.randrange(100),
    "ext_temp":  random.randrange(100),
    "humidity":  random.randrange(100),
    "wind_speed":  random.randrange(100),
    "wind_direction":  random.choice(['N', 'W', 'S', 'E']),
    "internal_temp": random.randrange(60),
    "uv": random.randrange(10),
    "battery_percentage": random.randrange(100),
}

r = requests.post(url=URL, json=data)
print(r.text)        



#then we basically just curl fake data to it