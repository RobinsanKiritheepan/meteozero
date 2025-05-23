from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime, timezone, timedelta
import os

app = Flask(__name__)

# Connexion MongoDB
client = MongoClient(os.environ.get("MONGO_URI"))
db = client["meteo_zero"]
collection = db["temperatures_zero"]

@app.route("/", methods=["GET"])
def index():
    return """
    <!DOCTYPE html>
    <html lang='fr'>
    <head>
        <meta charset='utf-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1'>
        <title>Station ZÉRO – Dashboard</title>
        <link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css' rel='stylesheet'>
        <style>
            body {
                background: linear-gradient(to right, #0f2027, #203a43, #2c5364);
                color: white;
                font-family: 'Segoe UI', sans-serif;
                margin: 0;
                padding: 0;
            }
            .container {
                padding: 2rem;
            }
            .thermo-wrapper {
                display: flex;
                justify-content: center;
                align-items: center;
                height: 250px;
                position: relative;
                background-color: #111;
                border-radius: 20px;
                box-shadow: 0 0 20px rgba(0,0,0,0.5);
            }
            .glass-thermo {
                width: 60px;
                height: 200px;
                background: linear-gradient(to top, #2e2e2e, #444);
                border-radius: 30px;
                position: relative;
                overflow: hidden;
                box-shadow: inset 0 0 20px rgba(255,255,255,0.1);
            }
            .glass-thermo::after {
                content: '';
                position: absolute;
                bottom: 0;
                width: 100%;
                height: 0%;
                background: linear-gradient(to top, #ff4e50, #f9d423);
                animation: fill 1s ease forwards;
                transition: height 0.5s ease;
                z-index: 1;
                border-radius: 30px 30px 0 0;
            }
            .temp-text {
                position: absolute;
                bottom: 10px;
                font-size: 2rem;
                font-weight: bold;
                color: white;
                text-shadow: 0 0 10px rgba(255,255,255,0.5);
            }
            .status {
                margin-top: 1rem;
                text-align: center;
                font-size: 1rem;
            }
            .average-box {
                margin-top: 2rem;
                background-color: #222;
                padding: 1rem;
                border-radius: 12px;
                text-align: center;
                font-size: 1.2rem;
                box-shadow: 0 0 10px rgba(0,0,0,0.4);
            }
        </style>
    </head>
    <body>
    <div class='container'>
        <h1 class='text-center mb-4'>🌡️ Station Météo ZÉRO</h1>
        <div class='thermo-wrapper'>
            <div class='glass-thermo' id='thermometer'></div>
            <div class='temp-text' id='temp'>--°C</div>
        </div>
        <div class='status' id='status-info'>Chargement...</div>
        <div class='average-box' id='avg-box'>📊 Moyenne 24h : --°C</div>
    </div>

    <script>
        async function update() {
            try {
                const [latestRes, avgRes] = await Promise.all([
                    fetch('/latest'),
                    fetch('/average')
                ]);
                const latest = await latestRes.json();
                const avg = await avgRes.json();

                const temp = latest.temp !== null ? latest.temp.toFixed(1) : '--';
                const status = latest.status || "unknown";
                document.getElementById('temp').innerText = temp + '°C';

                const percent = Math.min(100, Math.max(0, (temp / 100) * 100));
                document.querySelector('.glass-thermo::after');
                document.querySelector('.glass-thermo').style.setProperty('--fill-height', percent + '%');
                document.querySelector('.glass-thermo').style.setProperty('height', percent + '%');

                const statusText = {
                    "ok": "✅ Température à jour",
                    "offline": "❌ Capteur hors ligne",
                    "no_data": "⚠️ Aucune donnée reçue",
                    "ble": "📶 Attente config BLE",
                    "wifi": "📡 Attente capteur",
                    "erreur_capteur": "⚠️ Capteur non détecté",
                    "unknown": "❓ État inconnu"
                };
                document.getElementById('status-info').innerText = statusText[status] || statusText["unknown"];
                document.getElementById('avg-box').innerText = `📊 Moyenne 24h : ${avg.average !== null ? avg.average.toFixed(1) + '°C' : '--°C'}`;
            } catch (err) {
                document.getElementById('status-info').innerText = '❌ Erreur de connexion';
                document.getElementById('avg-box').innerText = '📊 Moyenne 24h : --°C';
            }
        }
        setInterval(update, 1000);
        update();
    </script>
    </body>
    </html>
    """

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

    status = "offline" if age > 5 else doc.get("status", "unknown")

    return jsonify({
        "temp": doc.get("temp", 0),
        "status": status,
        "timestamp": last_time.isoformat(),
        "age_seconds": age
    })

@app.route("/average", methods=["GET"])
def average_temp():
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    docs = list(collection.find({"timestamp": {"$gte": since}, "temp": {"$ne": None}}))
    if not docs:
        return jsonify({"average": None})
    avg = sum(d["temp"] for d in docs) / len(docs)
    return jsonify({"average": avg})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10001)
