import os, requests, sys

from flask import Flask, render_template, request
from pymongo import MongoClient
from dotenv import load_dotenv

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
    print(CONNECTION_STRING)
    client = MongoClient(CONNECTION_STRING)
    
    mode = client[db_name]['config'].find_one({"key": "mode"})["value"] #fix this
    print(f"Current mode: {mode}")

    label = None
    
    if mode == "regression_model":
        pass
        #get model file and use to predict
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
    client[db_name]["weather_data"].insert_one(json)

    return "Successful!"

    #publish to cache service
    

