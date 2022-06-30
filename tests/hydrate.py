import requests, random, os, datetime, bmemcached
import os, pymongo
from dotenv import load_dotenv

load_dotenv()

def get_mongo_handle():
    db_name = os.environ.get('MONGO_DB_NAME', None)
    CONNECTION_STRING = os.environ.get("MONGO_CONNECTION_STRING", None)
    client = pymongo.MongoClient(CONNECTION_STRING)
    return client[db_name] 

db = get_mongo_handle()

print("Hydrating test database and cache")
N = 100
for i in range(N):
    _json = {
        "baro_pressure": random.randrange(100),
        "ext_temp":  random.randrange(100),
        "humidity":  random.randrange(100),
        "wind_speed":  random.randrange(100),
        "gas_resistance":  random.randrange(50000),
        "wind_direction":  random.choice(['N', 'W', 'S', 'E']),
        "internal_temp": random.randrange(60),
        "precipitation_mmhr": random.randrange(500)*0.2974,
        "uv": random.randrange(10),
        "battery_percentage": random.randrange(100),
        "datetime": datetime.datetime.now() + datetime.timedelta(seconds=60*30*(i+1)),
        "label": random.choice([
            "Thunderstorm with light rain",
            "Thunderstorm with rain",
            "Thunderstorm with heavy rain",
            "Thunderstorm with light drizzle",
            "Thunderstorm with drizzle",
            "Thunderstorm with heavy drizzle",
            "Thunderstorm with Hail",
            "Light Drizzle",
            "Drizzle",
            "Heavy Drizzle",
            "Light Rain",
            "Moderate Rain",
            "Heavy Rain",
            "Freezing rain",
            "Light shower rain",
            "Shower rain",
            "Heavy shower rain",
            "Light snow",
            "Snow",
            "Heavy Snow",
            "Mix snow/rain",
            "Sleet",
            "Heavy sleet",
            "Snow shower",
            "Heavy snow shower",
            "Flurries",
            "Mist",
            "Smoke",
            "Haze",
            "Sand/dust",
            "Fog",
            "Freezing Fog",
            "Clear sky",
            "Few clouds",
            "Scattered clouds",
            "Broken clouds",
            "Overcast clouds",
            "Unknown Precipitation"])
    }

    db['weather_data'].insert_one(_json)
    print(f"Inserted {i+1}th item into db")
    if i == N-1:
        mc = bmemcached.Client(os.environ.get('MEMCACHEDCLOUD_SERVERS').split(','), os.environ.get('MEMCACHEDCLOUD_USERNAME'), os.environ.get('MEMCACHEDCLOUD_PASSWORD'))

        #get icon_image_url
        icon_map = {
            "Thunderstorm with light rain" : "t01",
            "Thunderstorm with rain" : "t02",
            "Thunderstorm with heavy rain" : "t03",
            "Thunderstorm with light drizzle" : "t04",
            "Thunderstorm with drizzle" : "t04",
            "Thunderstorm with heavy drizzle" : "t04",
            "Thunderstorm with Hail" : "t05",
            "Light Drizzle" : "d01",
            "Drizzle" : "d02",
            "Heavy Drizzle" : "d03",
            "Light Rain" : "r01",
            "Moderate Rain" : "r02",
            "Heavy Rain" : "r03",
            "Freezing rain" : "f01",
            "Light shower rain" : "r04",
            "Shower rain" : "r05",
            "Heavy shower rain" : "r06",
            "Light snow" : "s01",
            "Snow" : "s02",
            "Heavy Snow" : "s03",
            "Mix snow/rain" : "s04",
            "Sleet" : "s05",
            "Heavy sleet" : "s06",
            "Snow shower": "s01",
            "Heavy snow shower" : "s02",
            "Flurries" : "s06",
            "Mist" : "a01",
            "Smoke" : "a02",
            "Haze" : "a03",
            "Sand/dust": "a04",
            "Fog" : "a05",
            "Freezing Fog" : "a06",
            "Clear sky" : "c01",
            "Few clouds" : "c02",
            "Scattered clouds": "c02",
            "Broken clouds": "c03",
            "Overcast clouds": "c04",
            "Unknown Precipitation": "u00"
        }

        icon_code = icon_map[_json["label"]] 

        #get time
        timezonedb_key = os.environ.get("TIMEZONEDB_KEY", None)
        timezonedb_region = os.environ.get("TIMEZONEDB_REGION", None)
        timezonedb_req_string = f"http://api.timezonedb.com/v2.1/get-time-zone?key={timezonedb_key}&format=json&by=zone&zone={timezonedb_region}"
        r = requests.get(timezonedb_req_string)
        curr_hour_24h = int(r.json()["formatted"].split(' ')[1].split(":")[0])
        if curr_hour_24h >= 19 or curr_hour_24h <= 6:
            icon_code += "n"
        else:
            icon_code += "d"

        im_url = f"https://www.weatherbit.io/static/img/icons/{icon_code}.png"
        store = {
            "baro_pressure": _json["baro_pressure"],
            "ext_temp": _json["ext_temp"],
            "humidity": _json["humidity"], 
            "uv": _json["uv"], 
            "wind_speed": _json["wind_speed"],
            "wind_direction": _json["wind_direction"],
            "internal_temp": _json["internal_temp"],
            "label": _json["label"],
            "icon_image_url": im_url,
            "datetime" : _json["datetime"],
            "precipitation_mmhr" : _json["precipitation_mmhr"],
            "battery_percentage" : _json["battery_percentage"],
            "gas_resistance" : _json["gas_resistance"]
        }

        for k, v in store.items():
            mc.set(k, v)

        print("Inserted values into cache")
            
print("Hydration complete!")

