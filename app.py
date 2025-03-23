from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from helpers import *
from gemini import *
import json
#import db

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'Hello1234'  
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Where to redirect unlogged users


"""Databases"""
db = SQLAlchemy(app)
# User Table
class User(db.Model,UserMixin):
    id = db.Column(db.Integer, primary_key=True)  # Auto-incremented User ID
    username = db.Column(db.String(100), unique=True, nullable=False)  # Unique Username
    password_hash = db.Column(db.String(128), nullable=False)  # Store hashed password
    plants = db.relationship('Plant', backref='user', lazy=True)  # One-to-Many Relationship

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

# Plant Data Table
class Plant(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # Auto-incremented Plant ID
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Foreign Key
    plant_name = db.Column(db.String(100), nullable=False)  # Plant name
    plant_type = db.Column(db.String(100), nullable=False)  # Plant TYpe
    soil_type = db.Column(db.Text)  
    farming_practices=db.Column(db.Text)
    resources_available=db.Column(db.Text)
    lat=db.Column(db.Integer) #latitiude
    lon=db.Column(db.Integer) #longitude

#table with plant id , humidity , temperature_celcius , soil_moisture_percent, light_percent 
class Sensor_Data(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # Auto-incremented Plant ID
    plant_id = db.Column(db.Integer, db.ForeignKey('plant.id'), nullable=False)  # Foreign Key
    humidity = db.Column(db.Float)  # humidity
    temperature_celcius = db.Column(db.Float)  # temperature_celcius
    soil_moisture_percent = db.Column(db.Float)  # soil_moisture_percent
    light_percent = db.Column(db.Float)  # light_percent

"""Functions"""
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

"""Routes"""

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='Username already exists')

        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))  # Redirect to login after registration

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)  # Log the user in
            return redirect(url_for('dashboard'))  # Redirect to dashboard

        return render_template('login.html', error='Invalid username or password')

    return render_template('login.html')

@app.route('/dashboard')
@login_required  
def dashboard():
    query=Plant.query.filter(Plant.user_id==current_user.id)
    num_of_plants=query.count();
    plants_data=query.all();
    return render_template('dashboard.html', user=current_user,num_of_plants=num_of_plants,plants_data=plants_data , user_name=current_user.username,user_avatar=str(current_user.username)[0])  # Pass user info to template

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        user_id=current_user.id
        plant_name=request.form.get("plant_name")
        soil_type=request.form.get("soil_type")
        plant_type=request.form.get("plant_type")
        farming_practices=request.form.get("farming_practices")
        resources_available=request.form.get("resources_available")
        lat=request.form.get("lat")
        lon=request.form.get("lon")
        num_of_plants=Plant.query.filter(Plant.user_id==current_user.id).count();

        #check for error case
        if (num_of_plants>=5):
            return render_template("error.html",error="Can Only Store 5 Plants per user ")
        
        data= Plant(lat=lat,lon=lon ,resources_available=resources_available,farming_practices=farming_practices,user_id=user_id,plant_name=plant_name,soil_type=soil_type,plant_type=plant_type)
        db.session.add(data)
        db.session.commit()
        return redirect("/dashboard")  

    return render_template('add.html')

# @app.route('/<plant_id>/plant_dashboard')
# @login_required  
# def plant_dashboard(plant_id):
#     data=Plant.query.filter(Plant.id==plant_id).first()
#     if (current_user.id!=data.user_id):
#         return "Unauthorized Access"
#     weather_data=GetWeather(data.lat,data.lon)
#     weather_HTML=Humanize_JSON(weather_data,data.plant_type,data.soil_type,"Weather")
#     soil_data=GetSoil(data.lat,data.lon)
#     soil_HTML=Humanize_JSON(soil_data,data.plant_type,data.soil_type,"Soil Data from SoilGrids API")
#     suggestions=AI_Suggestions(data.lat,data.lon,data.resources_available,data.farming_practices,data.plant_type,data.soil_type,data.plant_name)
#     return render_template('plant_dashboard.html',soil_HTML=soil_HTML,weather_HTML=weather_HTML,suggestions=suggestions)

@app.route('/<plant_id>/plant_dashboard_V2')
@login_required  
def plant_dashboard_V2(plant_id):
    data=Plant.query.filter(Plant.id==plant_id).first()
    if (current_user.id!=data.user_id):
        return "Unauthorized Access"
    #check if the plant has any sensor data
    sensor_data=Sensor_Data.query.filter(Sensor_Data.plant_id==plant_id).first()
    sensor_available= 0 if sensor_data is None else 1
    return render_template('plant_dashboard.html',plant_name=data.plant_name,plant_id=plant_id,user_name=current_user.username,user_avatar=str(current_user.username)[0],sensor_available=sensor_available)

@app.route('/sensor', methods=['POST'])
def sensor_data():  
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        data_js= data.get('data')
        plant_id = data.get("plant_id")
        humidity = data_js.get("humidity")
        temperature_celcius = data_js.get("temp")
        soil_moisture_percent =data_js.get("moisture")
        light_percent = data_js.get("light")
        data=Sensor_Data(plant_id=plant_id,humidity=humidity,temperature_celcius=temperature_celcius,soil_moisture_percent=soil_moisture_percent,light_percent=light_percent)
        db.session.add(data)
        db.session.commit()
        return "Data Recieved"

@app.route('/<plant_id>/sensor_data')
@login_required
def sensor_data_route(plant_id):
    sensor_dataValue=Sensor_Data.query.filter(Sensor_Data.plant_id==plant_id).first()
    if sensor_dataValue is None:
        return "No Sensor Data Available"
    data=Plant.query.filter(Plant.id==plant_id).first()
    if (current_user.id!=data.user_id):
        return "Unauthorized Access"
    plant_data=Plant.query.filter(Plant.id==plant_id).first()
    json_data={"Moisture Percent":sensor_dataValue.soil_moisture_percent,"Temperature":sensor_dataValue.temperature_celcius,"Humidity Percent":sensor_dataValue.humidity,"Light Percent":sensor_dataValue.light_percent}
    units={"Moisture Percent":"Percent","Temperature":"Celcius","Humidity Percent":"Percent","Light Percent":"Percent"}
    
    sensor_HTML=Humanize_JSON(json_data,plant_data.plant_type,plant_data.soil_type,"Sensor Data")
    return render_template('basic.html',html_data=sensor_HTML,data=json_data,type="Sensor Data",units=units)

    
@app.route('/<plant_id>/suggestions', methods=['GET', 'POST'])
@login_required  
def suggestions_route(plant_id):
    data=Plant.query.filter(Plant.id==plant_id).first()
    if (current_user.id!=data.user_id):
        return "Unauthorized Access"
    sensor_dataValue=Sensor_Data.query.filter(Sensor_Data.plant_id==plant_id).first()
    issue = None
    if request.method == 'POST':
        issue = request.form['issues']

    if sensor_dataValue is not  None:
        Sensor_data={"Moisture Percent":sensor_dataValue.soil_moisture_percent,"Temperature":sensor_dataValue.temperature_celcius,"Humidity Percent":sensor_dataValue.humidity,"Light Percent":sensor_dataValue.light_percent}
        html=AI_Suggestions(data.lat,data.lon,data.resources_available,data.farming_practices,data.plant_type,data.soil_type,data.plant_name,Sensor_data=Sensor_data,issue=issue)
    else:
        html=AI_Suggestions(data.lat,data.lon,data.resources_available,data.farming_practices,data.plant_type,data.soil_type,data.plant_name,issue=issue)
    return render_template('basic.html',html_data=html,data={} ,type="Major Issues",units={})

@app.route('/<plant_id>/soil')
@login_required  
def soil_route(plant_id):
    data=Plant.query.filter(Plant.id==plant_id).first()
    if (current_user.id!=data.user_id):
        return "Unauthorized Access"
    soil_data=GetSoil(data.lat,data.lon)
    soil_HTML=Humanize_JSON(soil_data,data.plant_type,data.soil_type,"Soil Data from SoilGrids API")
    return render_template('basic.html',html_data=soil_HTML,type="Soil Data",data={},units={})


@app.route('/<plant_id>/weather')
@login_required  
def weather_route(plant_id):
    data=Plant.query.filter(Plant.id==plant_id).first()
    if (current_user.id!=data.user_id):
        return "Unauthorized Access"
    weather_data=GetWeather(data.lat,data.lon)
    weather_dict={"Temperature":weather_data["main"]["temp"],"Humidity":weather_data["main"]["humidity"],"Pressure":weather_data["main"]["pressure"],"Wind Speed":weather_data["wind"]["speed"],"Weather":weather_data["weather"][0]["description"]}
    units={"Temperature":"Kelvin","Humidity":"Percent","Pressure":"hPa","Wind Speed":"m/s","Weather":" "}
    weather_HTML=Humanize_JSON(weather_data,data.plant_type,data.soil_type,"Weather")
    return render_template('basic.html',html_data=weather_HTML,type="Weather Data",units=units,data=weather_dict)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Create the database tables if they don't exist
    # app.run(host="0.0.0.0",port="8080",debug=True)  # Run the app
    app.run()
