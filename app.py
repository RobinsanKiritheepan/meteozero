from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime, timezone
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
                    </div>
                </div>
            </div>

            <div class="col-md-8">
                <div class="chart-container">
                    <canvas id="chart"></canvas>
                </div>
            </div>
        </div>

        <div class="alert alert-info mt-4" id="help-box">
            <strong>🔧 Connexion initiale du Raspberry Pi Zero :</strong><br>
            Connecte-toi au Wi-Fi via l'interface BLE, ou démarre le script météo automatique.<br><br>
            <div id="status-info">⏳ En attente de connexion...</div>
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
                        title: (items) => `Temps: ${items[0].label}s`,
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
                        text: 'Temps (secondes)',
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
            }

            if (status === "ok") {
                history.push(data.temp);
                if (history.length > 120) history.shift();
                chart.data.labels = Array.from({ length: history.length }, (_, i) => i);
                chart.data.datasets[0].data = history;
                chart.update();
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10001)
