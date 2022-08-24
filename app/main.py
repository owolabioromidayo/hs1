import os, requests, sys, datetime, urllib.parse, bmemcached, json, datetime, pymongo, time, threading

from flask import Flask, render_template, request, send_file, redirect
from flask_cors import CORS

from bson.json_util import dumps
from dotenv import load_dotenv

import joblib
from sklearn.tree import DecisionTreeClassifier
import numpy
import pandas as pd

#image dependencies
import matplotlib.pyplot as plt
from sklearn import tree
from bson.binary import Binary

load_dotenv()

app = Flask(__name__, static_url_path='/static')
cors = CORS(app)

def get_mongo_handle():
    #connect to mongodb
    db_name = os.environ.get('MONGO_DB_NAME', None)
    CONNECTION_STRING = os.environ.get("MONGO_CONNECTION_STRING", None)
    client = pymongo.MongoClient(CONNECTION_STRING)
    return client[db_name] 

def train_model_from_server():
    #Send request and return (Non blocking from server)
    ML_ENDPOINT = os.environ.get("ML_ENDPOINT")
    TRAINING_PASSWORD = os.environ.get("TRAINING_PASSWORD")
    url = f"{ML_ENDPOINT}/train?password={TRAINING_PASSWORD}"
    requests.post(url = url)


def train_model():
    #wait and train the model (Blocking. which is why we thread it)
    
    print("Starting thread")
    db = get_mongo_handle()
    print("Starting requests")
    ML_ENDPOINT = os.environ.get("ML_ENDPOINT")
    TRAINING_PASSWORD = os.environ.get("TRAINING_PASSWORD")
    #startup?
    r = requests.post(url = ML_ENDPOINT, json={"password": TRAINING_PASSWORD})
    #cold starts? fsm need to do it twice
    r = requests.post(url = ML_ENDPOINT, json={"password": TRAINING_PASSWORD})
    print(r, r.content)
    print("Done with requests")

    #create image
    class_names = [
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
        "unknown precipitation"
    ]

    #get most recent model
    curr_model = db['ml'].find().sort('datetime', pymongo.DESCENDING)[0]

    with open('model.pkl', 'wb') as f:
        f.write(curr_model['file'])

    dtree_model = joblib.load("model.pkl")
    #generate model image
    print("Model loaded") 
    fig = plt.figure(figsize=(30,30))
    print("Figure objected created") 
    _ = tree.plot_tree(dtree_model,
                    feature_names=['baro_pressure', 'ext_temp', 'humidity', 'wind_speed', 'uv', 'precipitation_mmhr'],  
                    class_names=class_names,
                    filled=True)
                    
    print("Tree Image generated") 
    #Attempting image save
    with open("app/static/dtree.png", 'w+') as _:
                pass #create file

    print("Blank Image Created ") 
    fig.savefig("app/static/dtree.png")   

    print("Figure Saved.") 

    image_bin = None
    with open("app/static/dtree.png", "rb") as f:
        image_bin = Binary(f.read())

    print("Image binary read") 

    db['ml'].update_one({"datetime": curr_model['datetime']}, { "$set": { 'image-png': image_bin} })
    print("Done") 

    

@app.route("/status", methods=["GET"])
def get_current_status():
    #return weather station status, last update, update freq, uptime, battery percentage (will have to fix data first, mock on FE for now)
    update_freq_m = 30
    update_freq_w_buffer = 60*(update_freq_m+10) #30 minutes + 10 minute buffer
    db = get_mongo_handle()
    last_post = db["weather_data"].find_one({}, sort=[("_id", pymongo.DESCENDING)])
    first_post = db["weather_data"].find_one({}, sort=[("_id", pymongo.ASCENDING)])

    time_since_last_update = (datetime.datetime.now() - last_post["datetime"]).seconds
    time_since_first_post = (last_post["datetime"] - first_post["datetime"]).seconds / 60
    station_status = "Online" if time_since_last_update < update_freq_w_buffer else "Offline"
    
    _json = {
        "last_update_time" : str(last_post["datetime"]),
        "station_status" : station_status,
        "update_frequency": f"{update_freq_m} minutes",
        "uptime" : time_since_first_post , 
        "battery_percentage": last_post["battery_percentage"], #should be gotten from last post 
        }
    return json.dumps(_json, indent=4)


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
        "gas_resistance",
        "precipitation_mmhr",
        "uv",
        "label",
        "icon_image_url"                         
    ])

    return json.dumps(vals, indent=4)


@app.route("/weather_img", methods=["GET"])
def get_current_weather_img():
    mc = bmemcached.Client(os.environ.get('MEMCACHEDCLOUD_SERVERS').split(','), os.environ.get('MEMCACHEDCLOUD_USERNAME'), os.environ.get('MEMCACHEDCLOUD_PASSWORD'))
    vals = mc.get("icon_image_url")
    print(vals)
    return redirect(vals)

@app.route("/ml_img", methods=["GET"])
def get_current_ml_img():
    return send_file("static/dtree.png", mimetype="image/png")

@app.route("/ml_info", methods=["GET"])
def get_current_ml_info():
    db = get_mongo_handle()
    curr_model = db['ml'].find().sort('datetime', pymongo.DESCENDING)[0]

    percentage = curr_model["accuracy"] * 100
    _json  = {
        "accuracy" : f"{percentage}%",
        "description" : curr_model["description"],
        "last_update_time" : str(db['config'].find_one({"key": "last_model_update_time"})["value"]),
        "n_samples_used": curr_model["n_samples_used"] 
    }

    return json.dumps(_json, indent=4)


@app.route("/sensor_data/get", methods=["GET"])
def get_sensor():
    db = get_mongo_handle()
    collection = db["weather_data"]
    cursor = collection.find({})
    
    _json = {
        "ext_temp" : [],
        "baro_pressure": [],
        "wind_speed" : [],
        "uv": [],
        "humidity" : [],
        "gas_resistance" : [],
        "precipitation_mmhr" : [],
        "datetime": [],
        "battery_percentage": []
    }

    for entry in cursor:
        for k,v in _json.items():
            try:
                if k =="datetime":
                    v.append(entry[k].isoformat())
                    continue

                v.append(entry[k])
            except:
                pass

    return json.dumps(_json, indent=4)


@app.route("/sensor_data/publish", methods=["POST"])
def publish_sensors():
    if request.args.get("password") != os.environ.get("PUBLISH_PASSWORD"):
        return "Not authorized", 401

    ML_DEPLOYMENT = os.environ.get("ML_DEPLOYMENT")
    print(f"ML DEPLOYMENT METHOD: {ML_DEPLOYMENT}")
    #get json data
    _json = None
    content_type = request.headers.get('Content-Type')
    if (content_type == 'application/json'):
        _json = request.json
    else:
        return 'Content-Type not supported!'

    db = get_mongo_handle() 

    if not db['config'].find_one({"key": "mode"}):
        db['config'].insert_one({"key": "mode", "value": "weather_api"}) #default mode is weather_api

    mode = db['config'].find_one({"key": "mode"})["value"]

    print(f"Current mode: {mode}")
    label = None
    pred_label = None

    #we want to store the weather api label in the data regardless so the model gets more accurate over time even in ML mode
    #the predicted model, however, will be saved in the cache and that's what will be displayed
    lat = os.environ.get("LATITUDE", None)
    _long = os.environ.get("LONGITUDE", None)
    api_key = os.environ.get("WEATHERBIT_API_KEY", None)

    weatherbit_request_string = f"https://api.weatherbit.io/v2.0/current?lat={lat}&lon={_long}&key={api_key}"
    r = requests.get(weatherbit_request_string)
    label = r.json()["data"][0]["weather"]["description"]
    
    if mode == "machine_learning":  
        if not db['config'].find_one({"key": "last_model_update_time"}):
            db['config'].insert_one({"key": "last_model_update_time", "value": None}) #3 weeks default training frequency

        last_update = db['config'].find_one({"key": "last_model_update_time"})["value"] #get last update timestamp -> from mongo

        #set training_freq if not set
        if not db['config'].find_one({"key": "training_freq"}):
            db['config'].insert_one({"key": "training_freq", "value": 21}) #3 weeks default training frequency

        training_freq = db['config'].find_one({"key": "training_freq"})["value"]

        #retrain model if set time period has elapsed
        if not last_update or ( datetime.datetime.now() - last_update >= datetime.timedelta(days = training_freq) ):
            if ML_DEPLOYMENT == "LAMBDA":
                #prevent blocking with threads
                print("Retraining model...")
                thread = threading.Thread(target=train_model)
                thread.start()
            else:
                train_model_from_server()
        
        curr_model = None
        try:
            curr_model = db['ml'].find().sort('datetime', pymongo.DESCENDING)[0] #get most recent model file ( sort by date)
        except:
            return "Initial Model being trained. None for now", 204

        #update stored model if not current
        saved_model = os.path.isfile('model.pkl')
        saved_image = os.path.isfile("dtree.png")

        if ML_DEPLOYMENT != "LAMBDA" and saved_image: #image saving already occurs on the thread
            with open('app/static/dtree.png', 'w+') as _:
                pass #create file

            with open('app/static/dtree.png', 'wb') as f:
                f.write(curr_model['image-png'])

        if not saved_model:
            with open('model.pkl', 'w+') as _:
                pass #create file
            
            with open('model.pkl', 'wb') as f:
                f.write(curr_model['file'])


        elif not last_update or (last_update < curr_model['datetime']):
            with open('model.pkl', 'wb') as f:
                f.write(curr_model['file'])
            
            db['config'].update_one({"key": "last_model_update_time"}, { "$set": { 'value': datetime.datetime.now() } })
        
        loaded_model = joblib.load("model.pkl")

        #make prediction and save to label
        df = pd.DataFrame.from_dict({"baro_pressure": [_json["baro_pressure"]],
                                     "ext_temp": [_json["ext_temp"]],
                                     "humidity": [_json["humidity"]], 
                                     "wind_speed": [_json["wind_speed"]],
                                     "uv": [_json["uv"]],                                 
                                     "precipitation_mmhr": [_json["precipitation_mmhr"]],                                 
                                    })
        pred_label = loaded_model.predict(df)[0]

    else:                # mode == "weather_api"
        #use weather api
        pred_label = label


    #save labelled data to db
    _json["label"] = str(label).lower()
    _json["datetime" ] = datetime.datetime.now()
    db["weather_data"].insert_one(_json)

    #publish to cache service
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

    icon_code = icon_map[_json['label']] 

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
        "label": str(pred_label).lower(),
        "icon_image_url": im_url,
        "datetime" : _json["datetime"],
        "battery_percentage" : _json["battery_percentage"],
        "gas_resistance" : _json["gas_resistance"],
        "precipitation_mmhr" : _json["precipitation_mmhr"]
    }

    for k, v in store.items():
        mc.set(k, v)

    return "OK", 200

    
@app.route("/get_mode", methods=["GET"])
def get_mode():
    db = get_mongo_handle()
    if not db["config"].find_one({"key": "mode"}):
        db['config'].insert_one({"key": "mode", "value": "weather_api"}) #weather_api is default mode

    curr = db["config"].find_one({"key": "mode"})["value"]
    return curr, 200
    
@app.route("/toggle_mode", methods=["POST"])
def toggle_mode():
    db = get_mongo_handle()
    curr = db["config"].find_one({"key": "mode"})["value"]
    curr = "machine_learning" if curr == "weather_api" else "weather_api"

    db['config'].update_one({"key": "mode"}, { "$set": { 'value': curr} })
    return "OK", 200

@app.route("/get_training_freq", methods=["GET"])
def get_training_freq():
    db = get_mongo_handle()

    if not db['config'].find_one({"key": "training_freq"}):
        db['config'].insert_one({"key": "training_freq", "value": 21}) #3 weeks default training frequency
    
    curr = db["config"].find_one({"key": "training_freq"})["value"]
    return str(curr), 200
    
@app.route("/set_training_freq/<int:value>", methods=["POST"])
def set_training_freq(value):
    if value < 2 :
        return "Value too low", 400
        
    db = get_mongo_handle()
    db['config'].update_one({"key": "training_freq"}, { "$set": { 'value': value} })
    return "OK", 200
    