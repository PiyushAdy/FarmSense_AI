import os
import json
import requests
from helpers import *

# API Configuration
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# Generation configuration
generation_config = {
    "temperature": 1,
    "topP": 0.95,
    "topK": 40,
    "maxOutputTokens": 8192,
}

# Track conversation history
conversation_history = []

def send_request(prompt):
    """Send a request to the Gemini API and return the response"""
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    }
    
    # Build the request payload
    payload = {
        "contents": conversation_history + [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": generation_config
    }
    
    # Send the request
    response = requests.post(
        f"{API_URL}?key={GEMINI_API_KEY}", 
        headers=headers,
        json=payload
    )
    
    if response.status_code != 200:
        return f"Error: {response.status_code}, {response.text}"
    
    # Process and return the response
    response_data = response.json()
    if "candidates" in response_data and len(response_data["candidates"]) > 0:
        text_response = response_data["candidates"][0]["content"]["parts"][0]["text"]
        
        # Update conversation history
        conversation_history.append({"role": "user", "parts": [{"text": prompt}]})
        conversation_history.append({"role": "model", "parts": [{"text": text_response}]})
        
        return text_response
    else:
        return "No response generated"

def Humanize_JSON(data, plant_type, soil_type, info_type):
    prompt = f"""
    Interpret the given JSON data and give souggestions, for {info_type} and tell useful information for a farmer growing {plant_type} on {soil_type} soil in HTML format. 

    # Instructions
    1. Exclusively use the following tags: <h5>, <h6>, <b>, <li> ,<ul> , <u> and <p> . 
    2. The Response should not contain the provide JSON.
    3. Strictly refrain from using any of the following tags: <!DOCTYPE html>, <head>, <title>, <body>
    4. Use related LSI (Latent Semantic Indexing) keywords to enrich the content.
    5. Use friendly and encouraging tone English and follow the Simple friendly and encouraging tone English Wikipedia style guidelines.
    6. Subheadings should be underlined
    7. Response should strictly not include markdown 
    8. If some values are provided in api language like timestamps etc. then try to interpret the same for the given context and present in user readable format 
    9. The response would be presented to user directly so avoid using technical or non-user friendly terms 
    10. make all headings in bold 
    11. the suggestions and information should be detailed and informative
    Note: Failure to comply with the specified constraints will make the response invalid.
    JSON DATA 
    {str(data)}
    """
    
    return send_request(prompt)

def AI_Suggestions(lat, lon, resources, practices, plant_type, soil_type, plant_name, issue=None, Sensor_data=None):
    prompt = "Provide resolution to issue of " + issue + ". utilize the given data for more information " if (issue!=None and issue!="") else "give some suggestions for the farm on the basis of the given data"
    prompt += f"""
    1. latitude {lat}
    2. longitude {lon}
    3. Resources Available {resources}
    4. Farming Practices {practices}
    5. Plant Type {plant_type}
    6. Plant Name {plant_name}
    7. Soil Type {soil_type}
    8. Look into previous chats for more information
    """
    
    # Adding Sensor Data
    if Sensor_data is not None:
        prompt += f"""
        9. Sensor Data :: {Sensor_data}
        """
    
    # Adding Weather Data
    weather_data = GetWeather(lat, lon)
    prompt += f"""
    10. Weather Data :: {weather_data}
    """

    # Adding Instructions
    prompt += f"""
    # Instructions
    1. Exclusively use the following tags: <h5>, <h6>, <b>, <li> ,<ul> , <u> and <p> . 
    2. Try not to give the previously given recommendations again 
    3. Strictly refrain from using any of the following tags: <!DOCTYPE html>, <head>, <title>, <body>
    4. Use related LSI (Latent Semantic Indexing) keywords to enrich the content.
    5. Use friendly and encouraging tone English and follow the Simple friendly and encouraging tone English Wikipedia style guidelines.
    6. Incase of an error have some catchy and humourous phrase to cover it up without stating the error code
    7. response should strictly not include markdown
    8. make all headings in bold 
    9. All the subheadings should be underlined
    10. the suggestions and information should be detailed and informative
    
    Note: Failure to comply with the specified constraints will make the response invalid.
    """
    
    return send_request(prompt)


# print(Humanize_JSON(GetWeather(12.9716,79.1581),"Cotton","Normal","Weather Forecast"))
# print(Humanize_JSON(GetSoil(12.9716,79.1581),"Cotton","Normal","Soil"))
# print(AI_Suggestions(12.9716, 79.1581, ["water", "sunlight"], ["organic farming"], "fruit", "clay", "mango", "yellowing leaves"))