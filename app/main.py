import os, requests, sys, datetime

from flask import Flask, render_template, request
import pymongo
from dotenv import load_dotenv

import joblib
from sklearn.tree import DecisionTreeClassifier
import numpy
import pandas as pd

load_dotenv()


app = Flask(__name__)

#how do we implement the background scheduler
 
@app.route("/admin")
def control_view():
        #passworded control view 
        #contains weather api toggle, curr model, time until next training, data info(editable?)
        return "<h1>Heroku working!</h1>"

@app.route("/data")
def data_view():
    #return plots and all that
    return "<h1>Heroku working!</h1>"


@app.route("/sensor_data/publish", methods=["POST"])
def publish_sensors():

    #get json data
    json = None
    content_type = request.headers.get('Content-Type')
    if (content_type == 'application/json'):
        json = request.json
    else:
        return 'Content-Type not supported!'

    #connect to mongodb
    db_name = os.environ.get('MONGO_DB_NAME', None)
    CONNECTION_STRING = os.environ.get("MONGO_CONNECTION_STRING", None)
    client = pymongo.MongoClient(CONNECTION_STRING)
    db = client[db_name]
    
    mode = db['config'].find_one({"key": "mode"})["value"] 
    print(f"Current mode: {mode}")

    label = None
    
    if mode == "machine_learning":  
        last_update = db['config'].find_one({"key": "last_model_update_time"})["value"] #get last update timestamp -> from mongo

        #retrain model if set time period has elapsed
        training_freq = db['config'].find_one({"key": "training_freq"})["value"] 
        if datetime.datetime.now() - last_update >= datetime.timedelta(days = training_freq):
            print("Retraining model...")
            ML_ENDPOINT = os.environ.get("ML_ENDPOINT")
            requests.post(f"https://{ML_ENDPOINT}/train")
        
        curr_model = db['ml_test'].find().sort('datetime', pymongo.DESCENDING)[0] #get most recent model file ( sort by date)

        #update stored model if not current
        if last_update < curr_model['datetime']:
            with open('model.pkl', 'wb') as f:
                f.write(curr_model['file'])
            
            db['config'].update_one({"key": "last_model_update_time"}, { "$set": { 'value': datetime.datetime.now() } })
        
        loaded_model = joblib.load("model.pkl")

        #make prediction and save to label
        df = pd.DataFrame.from_dict({"baro_pressure": [json["baro_pressure"]],
                                     "ext_temp": [json["ext_temp"]],
                                     "humidity": [json["humidity"]], 
                                     "wind_speed": [json["wind_speed"]],
                                     "wind_direction": [json["wind_direction"]],                                 
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
    json["label"] = label
    db["weather_data"].insert_one(json)

    return "Successful!"

    #publish to cache service
    

