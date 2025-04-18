# FarmSense AI

FarmSense AI is an intelligent agricultural monitoring system that collects real-time environmental data to provide actionable insights for farmers. The system gathers humidity, temperature, light, and soil moisture readings and sends them to an AI model for analysis. It is designed to help optimize crop growth and improve farm efficiency using data-driven recommendations.

## 🔗 Live Demo
Access the hosted application at: [FarmSense AI](https://farmsenseai.ddns.net/)

## 🚀 Features
- **Real-time Data Collection using Arduino**: Gathers humidity, temperature, light, and soil moisture readings.
- **API integration for Soil and Weather** : Gathers additional data using SoilGrids and OpenWeather APIs
- **AI-Powered Insights**: Processes data using AI to provide actionable recommendations.
- **User-Friendly Dashboard**: Displays trends and analytics in an intuitive interface.
- **Remote Monitoring**: Access your farm's data from anywhere.
- **Personalized Query Resoulution**: Receive AI-powered suggestions for irrigation, fertilization, pest control, and harvesting based on your plant's current condition and environmental factors.
- **Linux Bluetooth Client**: Bluetooth Client to recieve data from Arduino and post it to the API 

## 🏗️ Tech Stack
- **Frontend**: HTML, CSS , JavaScript
- **Backend**: Flask (Python)
- **Database**: SQLite (Flask SQL_Alchemy)
- **Hardware**: Arduino with Sensors for humidity, temperature, light, and soil moisture
- **AI Model**: Gemini
- **Linux Bluetooth Client**:PyQT5
- **Arduino**:C/C++

## 🛠️ Setup Instructions
### Prerequisites
- Python 3.x
- Flask
- Required sensor modules

### Installation Steps
1. Clone the repository:
   ```sh
   git clone https://github.com/PiyushAdy/FarmSense_AI.git
   cd FarmSense_AI
   ```
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```

3. Run the Flask application:
   ```sh
   flask run
   ```
4. Access the app in your browser at `http://127.0.0.1:5000/`
   ## Arduino Setup
# Things Required
1. Arduino UNO R3
2. Soil Moisture Sensor
3. DHT11
4. HC05 Bluetooth Module
5. LDR Sensor
   
# Connections
1. Connect Moisture Sensor at pin A0
2. Comnect HC05 module at pin 10 & 11
3. Connect DHT-11 sensor at pin 8
4. Connect LDR sensor at pin A1

## 📊 Data Flow
1. Sensors and APIs collect environmental data.
3. Data is transmitted to the Flask backend via Linux Client .
4. The AI model processes data and generates insights.
5. Insights are displayed on the web dashboard.
6. Users receive recommendations.


## 📧 Contact
For any queries, contact [Piyush Ady](https://github.com/PiyushAdy).

---
**Happy Farming with AI! 🌱🚜**

