from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime, timezone, timedelta
import os
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import logging

# Configurer le logging pour débogage
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# MongoDB Connection
mongo_uri = os.environ.get("MONGO_URI")
if not mongo_uri:
    logger.error("MONGO_URI environment variable is not set")
    raise ValueError("MONGO_URI environment variable is not set")
client = MongoClient(mongo_uri)
db = client["meteo_zero"]
collection = db["temperatures_zero"]
notifications = db["notifications"]

# Twilio Configuration
twilio_enabled = True
twilio_client = None
twilio_whatsapp = os.environ.get("TWILIO_WHATSAPP_NUMBER")
try:
    twilio_sid = os.environ.get("TWILIO_SID")
    twilio_auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    if not twilio_sid or not twilio_auth_token:
        logger.warning("Twilio credentials not set. WhatsApp notifications will be disabled.")
        twilio_enabled = False
    else:
        twilio_client = Client(twilio_sid, twilio_auth_token)
except Exception as e:
    logger.error(f"Failed to initialize Twilio client: {e}")
    twilio_enabled = False

# Static files configuration
app.static_folder = 'static'

@app.route("/", methods=["GET"])
def index():
    logger.debug("Route / accessed, attempting to serve index.html")
    try:
        return app.send_static_file('index.html')
    except Exception as e:
        logger.error(f"Failed to serve index.html: {e}")
        return "Error: index.html not found", 404

@app.route("/temp", methods=["POST"])
def post_temp():
    data = request.json
    temp = data.get("temp")
    status = data.get("status", "unknown")
    doc = {
        "timestamp": datetime.now(timezone.utc),
        "status": status
    }
    if temp is not None:
        doc["temp"] = temp
    collection.insert_one(doc)
    
    if temp is not None and twilio_enabled:
        check_notifications(temp)
    
    return jsonify({"status": "ok"}), 200

@app.route("/latest", methods=["GET"])
def latest_temp():
    doc = collection.find_one(sort=[("timestamp", -1)])
    if not doc:
        return jsonify({
            "temp": None,
            "status": "no_data",
            "timestamp": None,
            "age_seconds": None
        })

    now = datetime.now(timezone.utc)
    last_time = doc.get("timestamp", now)
    if last_time.tzinfo is None:
        last_time = last_time.replace(tzinfo=timezone.utc)
    age = (now - last_time).total_seconds()

    if age > 5:
        status = "offline"
    else:
        status = doc.get("status", "unknown")

    return jsonify({
        "temp": doc.get("temp", 0),
        "status": status,
        "timestamp": last_time.isoformat(),
        "age_seconds": age
    })

@app.route("/daily-stats", methods=["GET"])
def daily_stats():
    now = datetime.now(timezone.utc)
    start_of_day = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    
    docs = collection.find({
        "timestamp": {"$gte": start_of_day},
        "temp": {"$exists": True}
    })
    
    temps = [doc["temp"] for doc in docs if doc.get("temp") is not None]
    
    if not temps:
        return jsonify({"avg": None, "min": None, "max": None})
    
    return jsonify({
        "avg": sum(temps) / len(temps),
        "min": min(temps),
        "max": max(temps)
    })

@app.route("/daily-data", methods=["GET"])
def daily_data():
    now = datetime.now(timezone.utc)
    start_of_day = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    
    docs = collection.find({
        "timestamp": {"$gte": start_of_day},
        "temp": {"$exists": True}
    }).sort("timestamp", 1)
    
    return jsonify([{
        "timestamp": doc["timestamp"].isoformat(),
        "temp": doc["temp"]
    } for doc in docs if doc.get("temp") is not None])

@app.route("/notifications", methods=["POST"])
def save_notifications():
    if not twilio_enabled:
        return jsonify({"status": "error", "message": "WhatsApp notifications are disabled"}), 503
    
    data = request.json
    number = data.get("number")
    threshold_high = data.get("threshold_high", 35)
    threshold_low = data.get("threshold_low", 5)
    
    if not number or not number.startswith('+'):
        return jsonify({"status": "error", "message": "Invalid phone number"}), 400
    
    notifications.update_one(
        {"number": number},
        {"$set": {
            "number": number,
            "threshold_high": threshold_high,
            "threshold_low": threshold_low,
            "last_notification": None
        }},
        upsert=True
    )
    
    return jsonify({"status": "ok"}), 200

@app.route("/history", methods=["GET"])
def get_history():
    start_date = request.args.get("start")
    end_date = request.args.get("end")
    
    if not start_date or not end_date:
        return jsonify({"error": "Start and end dates required"}), 400
    
    try:
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00')) + timedelta(days=1)
    except ValueError:
        return jsonify({"error": "Invalid date format"}), 400
    
    docs = collection.find({
        "timestamp": {"$gte": start, "$lte": end},
        "temp": {"$exists": True}
    }).sort("timestamp", 1)
    
    return jsonify([{
        "timestamp": doc["timestamp"].isoformat(),
        "temp": doc["temp"]
    } for doc in docs if doc.get("temp") is not None])

def check_notifications(temp):
    now = datetime.now(timezone.utc)
    users = notifications.find()
    
    for user in users:
        threshold_high = user.get("threshold_high", 35)
        threshold_low = user.get("threshold_low", 5)
        last_notification = user.get("last_notification")
        
        if last_notification and (now - last_notification).total_seconds() < 3600:
            continue
        
        message = None
        if temp > threshold_high:
            message = f"⚠️ Alerte : Température élevée à {temp:.1f}°C !"
        elif temp < threshold_low:
            message = f"⚠️ Alerte : Température basse à {temp:.1f}°C !"
        
        if message:
            try:
                twilio_client.messages.create(
                    body=message,
                    from_=f"whatsapp:{twilio_whatsapp}",
                    to=f"whatsapp:{user['number']}"
                )
                notifications.update_one(
                    {"number": user["number"]},
                    {"$set": {"last_notification": now}}
                )
            except TwilioRestException as e:
                logger.error(f"Twilio error: {e}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10001)