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
        <div id="status-info">殊 En attente de connexion...</div>
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

setInterval(update, 60000); // Update every 60 seconds
update();
</script>
</body>
</html>
