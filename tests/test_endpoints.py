import requests, random, os
from dotenv import load_dotenv

load_dotenv()
HOSTNAME = "http://127.0.0.1:5000"

print("Testing endpoints")

endpoints = [
    ["/weather_img", "Getting weather image", "get"],
    ["/get_mode", "Getting current mode", "get"],
    ["/toggle_mode", "Toggling mode", "post"],
    ["/get_mode", "Showing changes to mode", "get"],
    ["/toggle_mode", "Resetting mode", "post"],
    ["/status", "Get status info" , "get"],
    ["/weather", "Get weather info", "get"],
    ["/sensor_data/get", "Get all sensor data", "get"]
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