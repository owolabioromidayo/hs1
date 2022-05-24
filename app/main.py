import os, requests, sys, datetime, urllib.parse, bmemcached, json

from flask import Flask, render_template, request, send_file
from flask_cors import CORS
import pymongo
from dotenv import load_dotenv

import joblib
from sklearn.tree import DecisionTreeClassifier
import numpy
import pandas as pd

load_dotenv()

app = Flask(__name__, static_url_path='/static')
cors = CORS(app)


@app.route("/weather", methods=["GET"])
def get_current_weather():
    mc = bmemcached.Client(os.environ.get('MEMCACHEDCLOUD_SERVERS').split(','), os.environ.get('MEMCACHEDCLOUD_USERNAME'), os.environ.get('MEMCACHEDCLOUD_PASSWORD'))
    vals = mc.get_multi([
        "baro_pressure",
        "ext_temp",
        "humidity", 
        "wind_speed",
        "wind_direction",
        "internal_temp",
        "label",
        "icon_image_url"                         
    ])

    return json.dumps(vals, indent=4)

@app.route("/ml_img", methods=["GET"])
def get_current_ml_img():
    return send_file("static/dtree.png", mimetype="image/png")

@app.route("/ml_info", methods=["GET"])
def get_current_ml_info():
    #connect to mongodb
    db_name = os.environ.get('MONGO_DB_NAME', None)
    CONNECTION_STRING = os.environ.get("MONGO_CONNECTION_STRING", None)
    client = pymongo.MongoClient(CONNECTION_STRING)
    db = client[db_name]

    curr_model = db['ml_test'].find().sort('datetime', pymongo.DESCENDING)[0]

    percentage = curr_model["accuracy"] * 100
    _json  = {
        "accuracy" : f"{percentage}%",
        "description" : curr_model["description"],
        "datetime": str(curr_model["datetime"]),
        "confusion_matrix" : curr_model["confusion_matrix"]
    }

    return json.dumps(_json, indent=4)



@app.route("/sensor_data/publish", methods=["POST"])
def publish_sensors():
    if request.args.get("password") != os.environ.get("PUBLISH_PASSWORD"):
        return "Not authorized", 401

    #get json data
    _json = None
    content_type = request.headers.get('Content-Type')
    if (content_type == 'application/json'):
        _json = request.json
    else:
        return 'Content-Type not supported!'

    #connect to mongodb
    db_name = os.environ.get('MONGO_DB_NAME', None)
    CONNECTION_STRING = os.environ.get("MONGO_CONNECTION_STRING", None)
    client = pymongo.MongoClient(CONNECTION_STRING)
    db = client[db_name]
    
    # mode = db['config'].find_one({"key": "mode"})["value"] 
    mode = "weather_api"
    # mode = "machine_learning"

    print(f"Current mode: {mode}")

    label = None
    
    if mode == "machine_learning":  
        last_update = db['config'].find_one({"key": "last_model_update_time"})["value"] #get last update timestamp -> from mongo

        #retrain model if set time period has elapsed
        training_freq = db['config'].find_one({"key": "training_freq"})["value"] 
        if datetime.datetime.now() - last_update >= datetime.timedelta(days = training_freq):
            print("Retraining model...")
            ML_ENDPOINT = os.environ.get("ML_ENDPOINT")
            TRAINING_PASSWORD = os.environ.get("TRAINING_PASSWORD")
            requests.post(f"https://{ML_ENDPOINT}/train?password={TRAINING_PASSWORD}")
        
        curr_model = db['ml_test'].find().sort('datetime', pymongo.DESCENDING)[0] #get most recent model file ( sort by date)

        #update stored model if not current
        saved_model = os.path.isfile('model.pkl')
        saved_image = os.path.isfile("dtree.png")

        if not saved_image:
            with open('app/static/dtree.png', 'w+') as _:
                pass #create file

            with open('app/static/dtree.png', 'wb') as f:
                f.write(curr_model['image-png'])

        if not saved_model:
            with open('model.pkl', 'w+') as _:
                pass #create file
            
            with open('model.pkl', 'wb') as f:
                f.write(curr_model['file'])


        elif last_update < curr_model['datetime']:
            with open('model.pkl', 'wb') as f:
                f.write(curr_model['file'])
            
            db['config'].update_one({"key": "last_model_update_time"}, { "$set": { 'value': datetime.datetime.now() } })
        
        loaded_model = joblib.load("model.pkl")

        #make prediction and save to label
        df = pd.DataFrame.from_dict({"baro_pressure": [_json["baro_pressure"]],
                                     "ext_temp": [_json["ext_temp"]],
                                     "humidity": [_json["humidity"]], 
                                     "wind_speed": [_json["wind_speed"]],
                                     "wind_direction": [_json["wind_direction"]],                                 
                                    })
        label = loaded_model.predict(df)[0]

    elif mode == "weather_api":
        #use weather api
        lat = os.environ.get("LATITUDE", None)
        _long = os.environ.get("LONGITUDE", None)
        api_key = os.environ.get("WEATHERBIT_API_KEY", None)

        weatherbit_request_string = f"https://api.weatherbit.io/v2.0/current?lat={lat}&lon={_long}&key={api_key}"
        r = requests.get(weatherbit_request_string)
        label = r.json()["data"][0]["weather"]["description"]
    else:
        return "Failed! Operation mode not supported."


    #save labelled data to db
    _json["label"] = label
    db["weather_data"].insert_one(_json)

    #publish to cache service
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

    icon_code = icon_map[label] 

    #get time
    timezonedb_key = os.environ.get("TIMEZONEDB_KEY", None)
    timezonedb_req_string = f"http://api.timezonedb.com/v2.1/get-time-zone?key={timezonedb_key}&format=json&by=zone&zone=Africa/Lagos"
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
        "wind_speed": _json["wind_speed"],
        "wind_direction": _json["wind_direction"],
        "internal_temp": _json["internal_temp"],
        "label": _json["label"],
        "icon_image_url": im_url
    }

    for k, v in store.items():
        mc.set(k, v)

    return "Successful!"

    
    

