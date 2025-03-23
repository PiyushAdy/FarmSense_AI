import requests 
import os
from soilgrids import SoilGrids
import json

def GetWeather(lat,lon):
    API_Key=os.environ["OPEN_WEATHER_API_KEY"]
    data=requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_Key}")
    return data.json()


#function for soil data
def GetSoil(lat, lon):
    url = f"https://rest.isric.org/soilgrids/v2.0/properties/query?lat={lat}&lon={lon}"
    #https://rest.isric.org/soilgrids/v2.0/properties/query?bbox=79.1571,12.970600000000001,79.15910000000001,12.9726&property=clay,soc,phh2o&output=json
    response = requests.get(url)
    
    if response.status_code == 200:
        return response.json()  # Return JSON response
    else:
        return {"error": f"Failed to fetch data (Status code: {response.status_code})"}

#print(GetWeather(12.9716,79.1581))
#function for regional alerts from organizations (can include those from open weather as well)

#function for fertilizers/pesticides database

#function for market prices for crops 

#humanize/interpret the data using ai


# # Example usage
# latitude = 28.7041  # Replace with your latitude
# longitude = 77.1025  # Replace with your longitude

# soil_data = GetSoil(latitude, longitude)
# print(soil_data)  # Print the JSON response
