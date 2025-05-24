<<<<<<< HEAD
from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime, timezone, timedelta
import os
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

app = Flask(__name__)

# MongoDB Connection
client = MongoClient(os.environ.get("MONGO_URI"))
db = client["meteo_zero"]
collection = db["temperatures_zero"]
notifications = db["notifications"]

# Twilio Configuration
twilio_client = Client(os.environ.get("TWILIO_SID"), os.environ.get("TWILIO_AUTH_TOKEN"))
twilio_whatsapp = os.environ.get("TWILIO_WHATSAPP_NUMBER")

# Static files configuration
app.static_folder = 'static'

@app.route("/", methods=["GET"])
def index():
    return app.send_static_file('index.html')

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
    
    # Check for notifications
    if temp is not None:
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
        
        # Skip if notified within last hour
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
                print(f"Twilio error: {e}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10001)
=======
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Dashboard Température ZÉRO</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
    <style>
        body {
            font-family: 'Segoe UI', sans-serif;
            background: #0f0f0f;
            color: #fff;
        }
        .card-gradient {
            background: linear-gradient(135deg, #2c3e50 0%, #9b59b6 100%);
            border: none;
            border-radius: 15px;
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
            transition: transform 0.3s;
        }
        .card-gradient:hover {
            transform: translateY(-5px);
        }
        .chart-container {
            background: #1a1a1a;
            border-radius: 15px;
            padding: 20px;
        }
        .alert {
            border-radius: 12px;
            font-size: 0.95rem;
        }
        .stats-card {
            background: #2a2a2a;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
        }
        .history-table {
            background: #1a1a1a;
            border-radius: 10px;
            padding: 15px;
        }
    </style>
</head>
<body>
<nav class="navbar navbar-dark bg-black mb-4">
    <div class="container-fluid">
        <a class="navbar-brand" href="#">
            <i class="fas fa-thermometer-half me-2"></i>Station ZÉRO – Pi Zero 2 W
        </a>
    </div>
</nav>

<div class="container">
    <div class="row mb-4">
        <div class="col-md-4 mb-3">
            <div class="card card-gradient text-white">
                <div class="card-body text-center py-4">
                    <h3 class="mb-3"><i class="fas fa-fire me-2"></i>Température Actuelle</h3>
                    <div class="display-2 fw-bold mb-2" id="temp">--</div>
                    <div class="text-white-50 small" id="status">
                        <i class="fas fa-sync fa-spin"></i> Connexion...
                    </div>
                    <div class="mt-3">
                        <span id="trend" class="small"><i class="fas fa-arrow-right"></i> Tendance: --</span>
                    </div>
                </div>
            </div>
            <div class="stats-card">
                <h5>Statistiques du jour</h5>
                <p>Average: <span id="daily-avg">--</span>°C</p>
                <p>Min: <span id="daily-min">--</span>°C</p>
                <p>Max: <span id="daily-max">--</span>°C</p>
                <button class="btn btn-sm btn-outline-light" onclick="exportCSV()">Exporter CSV</button>
            </div>
            <div class="stats-card">
                <h5>Notifications WhatsApp</h5>
                <div class="mb-3">
                    <label for="whatsapp-number" class="form-label">Numéro WhatsApp (+33...)</label>
                    <input type="text" class="form-control" id="whatsapp-number" placeholder="+33612345678">
                </div>
                <div class="mb-3">
                    <label for="threshold-high" class="form-label">Seuil haut (°C)</label>
                    <input type="number" class="form-control" id="threshold-high" value="35">
                </div>
                <div class="mb-3">
                    <label for="threshold-low" class="form-label">Seuil bas (°C)</label>
                    <input type="number" class="form-control" id="threshold-low" value="5">
                </div>
                <button class="btn btn-sm btn-primary" onclick="saveNotificationSettings()">Enregistrer</button>
            </div>
        </div>

        <div class="col-md-8">
            <div class="chart-container">
                <canvas id="chart"></canvas>
            </div>
            <div class="history-table mt-3">
                <h5>Historique des données</h5>
                <div class="mb-3">
                    <label for="date-start" class="form-label">Date de début</label>
                    <input type="date" class="form-control" id="date-start">
                </div>
                <div class="mb-3">
                    <label for="date-end" class="form-label">Date de fin</label>
                    <input type="date" class="form-control" id="date-end">
                </div>
                <button class="btn btn-sm btn-outline-light" onclick="loadHistory()">Charger l'historique</button>
                <table class="table table-dark mt-3" id="history-table">
                    <thead>
                        <tr>
                            <th>Timestamp</th>
                            <th>Température (°C)</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
                <button class="btn btn-sm btn-outline-light" onclick="exportHistoryCSV()">Exporter l'historique</button>
            </div>
        </div>
    </div>

    <div class="alert alert-info mt-4" id="help-box">
        <strong>🔧 Connexion initiale du Raspberry Pi Zero :</strong><br>
        Connecte-toi au Wi-Fi via l'interface BLE, ou démarre le script météo automatique.<br><br>
        <div id="status-info">⏳ En attente de connexion...</div>
        <div id="alert-box" class="mt-2"></div>
    </div>
</div>

<script>
const ctx = document.getElementById('chart').getContext('2d');
const gradient = ctx.createLinearGradient(0, 0, 0, 400);
gradient.addColorStop(0, 'rgba(155, 89, 182, 0.6)');
gradient.addColorStop(1, 'rgba(155, 89, 182, 0.05)');

const chart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'Température (°C)',
            data: [],
            borderColor: '#9b59b6',
            backgroundColor: gradient,
            borderWidth: 3,
            pointRadius: 0,
            tension: 0.4,
            fill: true
        }]
    },
    options: {
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false },
            tooltip: {
                backgroundColor: 'rgba(0,0,0,0.9)',
                titleFont: { size: 16 },
                bodyFont: { size: 14 },
                callbacks: {
                    title: (items) => `Temps: ${items[0].label}`,
                    label: (item) => `→ ${item.formattedValue}°C`
                }
            }
        },
        scales: {
            x: {
                grid: { color: 'rgba(255,255,255,0.1)' },
                ticks: { color: '#fff' },
                title: {
                    display: true,
                    text: 'Temps',
                    color: '#fff'
                }
            },
            y: {
                min: 0,
                max: 100,
                grid: { color: 'rgba(255,255,255,0.1)' },
                ticks: { color: '#fff' },
                title: {
                    display: true,
                    text: 'Température (°C)',
                    color: '#fff'
                }
            }
        }
    }
});

let history = [];
let lastTemps = [];

async function update() {
    try {
        const response = await fetch('/latest');
        const data = await response.json();

        const statusText = {
            "ble": "📶 En attente de configuration Wi-Fi via BLE...",
            "wifi": "📡 Connecté au Wi-Fi, attente du capteur...",
            "ok": "✅ Température à jour",
            "offline": "❌ Capteur déconnecté du réseau",
            "no_data": "⚠️ Aucune donnée reçue encore",
            "erreur_capteur": "⚠️ Capteur non détecté (SPI)",
            "unknown": "❓ État inconnu"
        };

        const statusColor = {
            "ok": "text-success",
            "ble": "text-warning",
            "wifi": "text-warning",
            "erreur_capteur": "text-danger",
            "offline": "text-danger",
            "no_data": "text-warning",
            "unknown": "text-secondary"
        };

        const status = data.status || "unknown";

        if (status === "offline" || status === "no_data") {
            document.getElementById('temp').innerHTML = "--";
        } else if (data.temp !== null && data.temp !== undefined) {
            document.getElementById('temp').innerHTML = `${data.temp.toFixed(1)}<small class="fs-6">°C</small>`;
            
            // Trend calculation
            lastTemps.push(data.temp);
            if (lastTemps.length > 5) lastTemps.shift();
            let trend = "Stable";
            if (lastTemps.length >= 2) {
                const diff = lastTemps[lastTemps.length - 1] - lastTemps[0];
                trend = diff > 0.5 ? "En hausse 📈" : diff < -0.5 ? "En baisse 📉" : "Stable ➡️";
            }
            document.getElementById('trend').innerHTML = `<i class="fas fa-arrow-right"></i> Tendance: ${trend}`;
        }

        if (status === "ok") {
            history.push({temp: data.temp, time: new Date().toLocaleTimeString()});
            if (history.length > 60) history.shift();
            chart.data.labels = history.map(h => h.time);
            chart.data.datasets[0].data = history.map(h => h.temp);
            chart.update();
        }

        // Update daily stats
        const statsResponse = await fetch('/daily-stats');
        const stats = await statsResponse.json();
        document.getElementById('daily-avg').textContent = stats.avg ? stats.avg.toFixed(1) : '--';
        document.getElementById('daily-min').textContent = stats.min ? stats.min.toFixed(1) : '--';
        document.getElementById('daily-max').textContent = stats.max ? stats.max.toFixed(1) : '--';

        // Temperature alerts
        const alertBox = document.getElementById('alert-box');
        if (data.temp > 35) {
            alertBox.innerHTML = '<div class="alert alert-danger">⚠️ Température élevée !</div>';
        } else if (data.temp < 5) {
            alertBox.innerHTML = '<div class="alert alert-warning">⚠️ Température basse !</div>';
        } else {
            alertBox.innerHTML = '';
        }

        document.getElementById('status-info').innerHTML = statusText[status] || "❓ État non reconnu";
        const statusEl = document.getElementById('status');
        statusEl.innerHTML = `<i class="fas fa-circle me-1"></i> ${new Date().toLocaleTimeString()}`;
        statusEl.className = `text-white-50 small ${statusColor[status] || ''}`;
    } catch (error) {
        document.getElementById('status').innerHTML = `
            <i class="fas fa-exclamation-triangle text-danger"></i> Erreur de connexion
        `;
        document.getElementById('status-info').innerHTML = "❌ Serveur injoignable ou Pi Zero hors ligne.";
    }
}

async function exportCSV() {
    try {
        const response = await fetch('/daily-data');
        const data = await response.json();
        const csv = ['Timestamp,Température (°C)'];
        data.forEach(d => {
            csv.push(`${d.timestamp},${d.temp}`);
        });
        const blob = new Blob([csv.join('\n')], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'temperature_data.csv';
        a.click();
        window.URL.revokeObjectURL(url);
    } catch (error) {
        alert('Erreur lors de l\'exportation des données');
    }
}

async function saveNotificationSettings() {
    const number = document.getElementById('whatsapp-number').value;
    const high = parseFloat(document.getElementById('threshold-high').value);
    const low = parseFloat(document.getElementById('threshold-low').value);

    if (!number || !number.startsWith('+')) {
        alert('Veuillez entrer un numéro WhatsApp valide avec le code pays (ex: +33612345678)');
        return;
    }

    try {
        const response = await fetch('/notifications', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ number, threshold_high: high, threshold_low: low })
        });
        const result = await response.json();
        if (result.status === 'ok') {
            alert('Paramètres de notification enregistrés !');
        } else {
            alert('Erreur lors de l\'enregistrement des paramètres.');
        }
    } catch (error) {
        alert('Erreur de connexion au serveur.');
    }
}

async function loadHistory() {
    const start = document.getElementById('date-start').value;
    const end = document.getElementById('date-end').value;

    if (!start || !end) {
        alert('Veuillez sélectionner une plage de dates.');
        return;
    }

    try {
        const response = await fetch(`/history?start=${start}&end=${end}`);
        const data = await response.json();
        const tbody = document.querySelector('#history-table tbody');
        tbody.innerHTML = '';
        data.forEach(d => {
            const row = document.createElement('tr');
            row.innerHTML = `<td>${new Date(d.timestamp).toLocaleString()}</td><td>${d.temp.toFixed(1)}</td>`;
            tbody.appendChild(row);
        });
    } catch (error) {
        alert('Erreur lors du chargement de l\'historique.');
    }
}

async function exportHistoryCSV() {
    const start = document.getElementById('date-start').value;
    const end = document.getElementById('date-end').value;

    if (!start || !end) {
        alert('Veuillez sélectionner une plage de dates.');
        return;
    }

    try {
        const response = await fetch(`/history?start=${start}&end=${end}`);
        const data = await response.json();
        const csv = ['Timestamp,Température (°C)'];
        data.forEach(d => {
            csv.push(`${d.timestamp},${d.temp}`);
        });
        const blob = new Blob([csv.join('\n')], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `temperature_history_${start}_${end}.csv`;
        a.click();
        window.URL.revokeObjectURL(url);
    } catch (error) {
        alert('Erreur lors de l\'exportation de l\'historique.');
    }
}

setInterval(update, 60000); // Update every 60 seconds
update();
</script>
</body>
</html>
>>>>>>> dc209e1655e30e8bd03d1b250a43ebf74ba11362
