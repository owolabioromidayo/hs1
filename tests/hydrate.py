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
            "thunderstorm with light rain",
            "thunderstorm with rain" ,
            "thunderstorm with heavy rain" ,
            "thunderstorm with light drizzle",
            "thunderstorm with drizzle" ,
            "thunderstorm with heavy drizzle" ,
            "thunderstorm with hail" ,
            "light drizzle",
            "drizzle",
            "heavy drizzle",
            "light rain",
            "moderate rain",
            "heavy rain",
            "freezing rain",
            "light shower rain",
            "shower rain",
            "heavy shower rain",
            "light snow",
            "snow",
            "heavy snow",
            "mix snow/rain",
            "sleet",
            "heavy sleet" ,
            "snow shower",
            "heavy snow shower",
            "flurries" ,
            "mist" ,
            "smoke" ,
            "haze",
            "sand/dust",
            "fog" ,
            "freezing fog",
            "clear sky",
            "few clouds",
            "scattered clouds",
            "broken clouds",
            "overcast clouds",
            "unknown precipitation"])
    }

    db['weather_data'].insert_one(_json)
    print(f"Inserted {i+1}th item into db")
    if i == N-1:
        mc = bmemcached.Client(os.environ.get('MEMCACHEDCLOUD_SERVERS').split(','), os.environ.get('MEMCACHEDCLOUD_USERNAME'), os.environ.get('MEMCACHEDCLOUD_PASSWORD'))

        #get icon_image_url
        icon_map = {
            "thunderstorm with light rain" : "t01",
            "thunderstorm with rain" : "t02",
            "thunderstorm with heavy rain" : "t03",
            "thunderstorm with light drizzle" : "t04",
            "thunderstorm with drizzle" : "t04",
            "thunderstorm with heavy drizzle" : "t04",
            "thunderstorm with hail" : "t05",
            "light drizzle" : "d01",
            "drizzle" : "d02",
            "heavy drizzle" : "d03",
            "light rain" : "r01",
            "moderate rain" : "r02",
            "heavy rain" : "r03",
            "freezing rain" : "f01",
            "light shower rain" : "r04",
            "shower rain" : "r05",
            "heavy shower rain" : "r06",
            "light snow" : "s01",
            "snow" : "s02",
            "heavy snow" : "s03",
            "mix snow/rain" : "s04",
            "sleet" : "s05",
            "heavy sleet" : "s06",
            "snow shower": "s01",
            "heavy snow shower" : "s02",
            "flurries" : "s06",
            "mist" : "a01",
            "smoke" : "a02",
            "haze" : "a03",
            "sand/dust": "a04",
            "fog" : "a05",
            "freezing fog" : "a06",
            "clear sky" : "c01",
            "few clouds" : "c02",
            "scattered clouds": "c02",
            "broken clouds": "c03",
            "overcast clouds": "c04",
            "unknown precipitation": "u00"
        }

        icon_code = icon_map[str(_json["label"]).lower()] 

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

