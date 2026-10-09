from flask import Flask, jsonify, request, render_template_string
import psutil
import socket
import time
import random
import io
import base64
import os
from datetime import datetime

# Optional AI
try:
    from sklearn.ensemble import IsolationForest
    AI_AVAILABLE = True
except Exception:
    AI_AVAILABLE = False

# Optional QR
try:
    import qrcode
    QR_AVAILABLE = True
except Exception:
    QR_AVAILABLE = False


app = Flask(__name__)


# =========================================================
# DATA
# =========================================================

devices = [
    {
        "id": 1,
        "name": "Admin Laptop",
        "ip": "192.168.1.10",
        "type": "Laptop",
        "status": "Online",
        "risk": 12
    },
    {
        "id": 2,
        "name": "Lab Router",
        "ip": "192.168.1.1",
        "type": "Router",
        "status": "Online",
        "risk": 8
    },
    {
        "id": 3,
        "name": "Student PC",
        "ip": "192.168.1.25",
        "type": "Computer",
        "status": "Online",
        "risk": 18
    }
]

threats = []
history = []

previous_net = psutil.net_io_counters()
previous_time = time.time()

simulation_mode = False

# AI model
ai_model = None


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def get_local_ip():
    """Get the local IP address of this computer."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except Exception:
        return "127.0.0.1"


def initialize_ai():
    """Create a simple Isolation Forest model."""
    global ai_model

    if not AI_AVAILABLE:
        return

    try:
        normal_data = []

        for _ in range(150):
            mbps = random.uniform(0.5, 8.0)
            packets = random.uniform(20, 250)
            normal_data.append([mbps, packets])

        ai_model = IsolationForest(
            contamination=0.08,
            random_state=42
        )

        ai_model.fit(normal_data)

    except Exception:
        ai_model = None


def get_network_data():
    """Collect current network activity."""
    global previous_net
    global previous_time

    try:
        current_net = psutil.net_io_counters()
        current_time = time.time()

        time_diff = max(current_time - previous_time, 0.1)

        bytes_sent = max(
            current_net.bytes_sent - previous_net.bytes_sent,
            0
        )

        bytes_recv = max(
            current_net.bytes_recv - previous_net.bytes_recv,
            0
        )

        packets_sent = max(
            current_net.packets_sent - previous_net.packets_sent,
            0
        )

        packets_recv = max(
            current_net.packets_recv - previous_net.packets_recv,
            0
        )

        total_bytes = bytes_sent + bytes_recv
        total_packets = packets_sent + packets_recv

        mbps = (total_bytes * 8) / time_diff / 1_000_000
        packets_per_sec = total_packets / time_diff

        # Safe demo simulation
        if simulation_mode:
            mbps += random.uniform(8, 25)
            packets_per_sec += random.uniform(150, 600)

        try:
            connections = len(psutil.net_connections())
        except Exception:
            connections = 0

        previous_net = current_net
        previous_time = current_time

        return {
            "mbps": round(mbps, 2),
            "packets": round(packets_per_sec, 2),
            "connections": connections
        }

    except Exception:
        return {
            "mbps": 0,
            "packets": 0,
            "connections": 0
        }


def calculate_ai_risk(data):
    """Calculate network risk using AI or fallback rules."""
    mbps = float(data.get("mbps", 0))
    packets = float(data.get("packets", 0))

    # Simulation mode gives a higher risk score
    if simulation_mode:
        return random.randint(70, 95)

    if ai_model is not None:
        try:
            prediction = ai_model.predict([[mbps, packets]])[0]

            if prediction == -1:
                score = random.randint(65, 92)
            else:
                score = random.randint(5, 25)

            return score

        except Exception:
            pass

    # Fallback rule-based risk
    score = 5

    if mbps > 20:
        score += 25
    elif mbps > 10:
        score += 15

    if packets > 700:
        score += 35
    elif packets > 400:
        score += 20

    return min(score, 95)


def get_health(risk):
    if risk < 25:
        return "Excellent"
    elif risk < 50:
        return "Good"
    elif risk < 75:
        return "Warning"
    else:
        return "Critical"


def create_qr():
    """Generate QR code for local network access."""
    if not QR_AVAILABLE:
        return None

    try:
        ip = get_local_ip()
        url = f"http://{ip}:5000"

        qr = qrcode.QRCode(
            version=1,
            box_size=8,
            border=4
        )

        qr.add_data(url)
        qr.make(fit=True)

        image = qr.make_image()

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")

        encoded = base64.b64encode(
            buffer.getvalue()
        ).decode("utf-8")

        return {
            "url": url,
            "image": f"data:image/png;base64,{encoded}"
        }

    except Exception:
        return None


# =========================================================
# API - DASHBOARD
# =========================================================

@app.route("/api/dashboard")
def dashboard():

    data = get_network_data()

    risk = calculate_ai_risk(data)

    health = get_health(risk)

    online_devices = sum(
        1 for device in devices
        if device["status"] == "Online"
    )

    active_threats = sum(
        1 for threat in threats
        if threat["status"] == "Active"
    )

    timestamp = datetime.now().strftime("%H:%M:%S")

    history.append({
        "time": timestamp,
        "mbps": data["mbps"],
        "packets": data["packets"],
        "risk": risk
    })

    # Keep only latest 30 records
    if len(history) > 30:
        history.pop(0)

    return jsonify({
        "bandwidth": data["mbps"],
        "packets": data["packets"],
        "connections": data["connections"],
        "devices": online_devices,
        "total_devices": len(devices),
        "threats": active_threats,
        "risk": risk,
        "health": health,
        "ai_available": AI_AVAILABLE,
        "simulation": simulation_mode,
        "time": timestamp
    })


# =========================================================
# API - HISTORY
# =========================================================

@app.route("/api/history")
def get_history():
    return jsonify(history)


# =========================================================
# API - DEVICES
# =========================================================

@app.route("/api/devices")
def get_devices():
    return jsonify(devices)


@app.route("/api/devices/add", methods=["POST"])
def add_device():

    data = request.get_json(silent=True) or {}

    name = str(data.get("name", "")).strip()
    ip = str(data.get("ip", "")).strip()
    device_type = str(data.get("type", "Computer")).strip()

    if not name or not ip:
        return jsonify({
            "success": False,
            "message": "Name and IP address are required."
        }), 400

    new_id = max(
        [device["id"] for device in devices],
        default=0
    ) + 1

    new_device = {
        "id": new_id,
        "name": name,
        "ip": ip,
        "type": device_type,
        "status": "Online",
        "risk": random.randint(5, 25)
    }

    devices.append(new_device)

    return jsonify({
        "success": True,
        "device": new_device
    })


@app.route("/api/devices/edit/<int:device_id>", methods=["PUT"])
def edit_device(device_id):

    data = request.get_json(silent=True) or {}

    for device in devices:

        if device["id"] == device_id:

            if "name" in data:
                device["name"] = str(data["name"]).strip()

            if "ip" in data:
                device["ip"] = str(data["ip"]).strip()

            if "type" in data:
                device["type"] = str(data["type"]).strip()

            return jsonify({
                "success": True,
                "device": device
            })

    return jsonify({
        "success": False,
        "message": "Device not found."
    }), 404


@app.route("/api/devices/delete/<int:device_id>", methods=["DELETE"])
def delete_device(device_id):

    global devices

    original_length = len(devices)

    devices = [
        device
        for device in devices
        if device["id"] != device_id
    ]

    if len(devices) == original_length:
        return jsonify({
            "success": False,
            "message": "Device not found."
        }), 404

    return jsonify({
        "success": True
    })


# =========================================================
# API - THREAT SIMULATION
# =========================================================

@app.route("/api/simulate_threat", methods=["POST"])
def simulate_threat():

    global simulation_mode

    simulation_mode = True

    threat_id = max(
        [threat["id"] for threat in threats],
        default=0
    ) + 1

    threat_types = [
        "Abnormal Traffic",
        "Packet Flood",
        "Suspicious Network Activity",
        "Unusual Bandwidth Spike"
    ]

    severities = [
        "Medium",
        "High",
        "Critical"
    ]

    new_threat = {
        "id": threat_id,
        "type": random.choice(threat_types),
        "severity": random.choice(severities),
        "source": random.choice([
            "192.168.1.25",
            "192.168.1.45",
            "192.168.1.77"
        ]),
        "time": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "status": "Active"
    }

    threats.append(new_threat)

    return jsonify({
        "success": True,
        "threat": new_threat
    })


@app.route("/api/threats")
def get_threats():
    return jsonify(threats)


@app.route("/api/threats/resolve/<int:threat_id>", methods=["POST"])
def resolve_threat(threat_id):

    global simulation_mode

    for threat in threats:

        if threat["id"] == threat_id:

            threat["status"] = "Resolved"

            active_count = sum(
                1 for item in threats
                if item["status"] == "Active"
            )

            if active_count == 0:
                simulation_mode = False

            return jsonify({
                "success": True,
                "threat": threat
            })

    return jsonify({
        "success": False,
        "message": "Threat not found."
    }), 404


# =========================================================
# API - AI ASSISTANT
# =========================================================

@app.route("/api/assistant", methods=["POST"])
def assistant():

    data = request.get_json(silent=True) or {}

    question = str(
        data.get("question", "")
    ).strip().lower()

    current_data = get_network_data()

    risk = calculate_ai_risk(current_data)

    active_threats = sum(
        1 for threat in threats
        if threat["status"] == "Active"
    )

    if not question:
        answer = "Please enter a question."

    elif "health" in question:
        answer = (
            f"Current network health is "
            f"{get_health(risk)} with an AI risk score of {risk}%."
        )

    elif "threat" in question:
        answer = (
            f"There are {active_threats} active threat(s). "
            f"The current AI risk score is {risk}%."
        )

    elif "device" in question:
        answer = (
            f"The system currently monitors "
            f"{len(devices)} device(s)."
        )

    elif "bandwidth" in question:
        answer = (
            f"Current network bandwidth is "
            f"{current_data['mbps']} Mbps."
        )

    elif "packet" in question:
        answer = (
            f"Current packet rate is "
            f"{current_data['packets']} packets/sec."
        )

    elif "report" in question:
        answer = (
            "You can open the Reports section to view "
            "the latest network monitoring summary."
        )

    elif "ai" in question:
        if AI_AVAILABLE:
            answer = (
                "AI monitoring is active using an "
                "Isolation Forest anomaly detection model."
            )
        else:
            answer = (
                "AI library is unavailable, so the system "
                "is currently using fallback rule-based detection."
            )

    else:
        answer = (
            "I can help with network health, bandwidth, "
            "packets, devices, threats, AI status and reports."
        )

    return jsonify({
        "answer": answer
    })


# =========================================================
# API - QR
# =========================================================

@app.route("/api/qr")
def qr_api():

    qr_data = create_qr()

    if qr_data is None:
        return jsonify({
            "success": False,
            "message": "QR generation is unavailable."
        })

    return jsonify({
        "success": True,
        "url": qr_data["url"],
        "image": qr_data["image"]
    })


# =========================================================
# API - REPORT
# =========================================================

@app.route("/api/report")
def report():

    data = get_network_data()

    risk = calculate_ai_risk(data)

    active_threats = sum(
        1 for threat in threats
        if threat["status"] == "Active"
    )

    online_devices = sum(
        1 for device in devices
        if device["status"] == "Online"
    )

    return jsonify({
        "generated_at": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "bandwidth": data["mbps"],
        "packets": data["packets"],
        "connections": data["connections"],
        "devices": len(devices),
        "online_devices": online_devices,
        "active_threats": active_threats,
        "risk": risk,
        "health": get_health(risk),
        "ai_status": (
            "Available"
            if AI_AVAILABLE
            else "Fallback Mode"
        )
    })


# =========================================================
# MAIN PAGE
# =========================================================

HTML = """
<!DOCTYPE html>
<html lang="en">

<head>

    <meta charset="UTF-8">

    <meta name="viewport"
          content="width=device-width, initial-scale=1.0">

    <title>NetShield AI</title>

    <link rel="preconnect"
          href="https://fonts.googleapis.com">

    <link rel="preconnect"
          href="https://fonts.gstatic.com"
          crossorigin>

    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Poppins:wght@400;500;600;700&display=swap"
          rel="stylesheet">

    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>


    <style>

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Poppins', sans-serif;
            background:
                radial-gradient(
                    circle at top right,
                    rgba(92, 67, 180, 0.20),
                    transparent 35%
                ),
                #070914;
            color: #f4f7ff;
            min-height: 100vh;
        }

        button,
        input,
        select {
            font-family: inherit;
        }

        .layout {
            display: flex;
            min-height: 100vh;
        }

        .sidebar {
            width: 245px;
            background: rgba(9, 12, 28, 0.96);
            border-right: 1px solid #202744;
            padding: 25px 16px;
            position: fixed;
            top: 0;
            bottom: 0;
            left: 0;
        }

        .logo {
            font-size: 22px;
            font-weight: 700;
            margin-bottom: 35px;
            color: #8f7cff;
        }

        .logo span {
            color: #42e8a7;
        }

        .nav-btn {
            width: 100%;
            border: 0;
            background: transparent;
            color: #8992ad;
            padding: 13px 14px;
            margin-bottom: 7px;
            border-radius: 12px;
            text-align: left;
            cursor: pointer;
            transition: 0.2s;
            font-size: 14px;
        }

        .nav-btn:hover,
        .nav-btn.active {
            background: rgba(126, 105, 255, 0.15);
            color: #ffffff;
        }

        .main {
            margin-left: 245px;
            width: calc(100% - 245px);
            padding: 28px;
        }

        .topbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
        }

        .title h1 {
            font-size: 27px;
        }

        .title p {
            color: #7d86a4;
            margin-top: 4px;
            font-size: 13px;
        }

        .status {
            display: flex;
            align-items: center;
            gap: 8px;
            background: rgba(66, 232, 167, 0.08);
            border: 1px solid rgba(66, 232, 167, 0.25);
            padding: 9px 13px;
            border-radius: 20px;
            font-size: 12px;
            color: #42e8a7;
        }

        .dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #42e8a7;
            box-shadow: 0 0 12px #42e8a7;
        }

        .section {
            display: none;
        }

        .section.active {
            display: block;
        }

        .cards {
            display: grid;
            grid-template-columns:
                repeat(auto-fit, minmax(190px, 1fr));
            gap: 15px;
            margin-bottom: 18px;
        }

        .card {
            background: rgba(16, 20, 40, 0.92);
            border: 1px solid #222a49;
            border-radius: 17px;
            padding: 19px;
            box-shadow: 0 10px 35px rgba(0, 0, 0, 0.15);
        }

        .card-label {
            color: #7e88a6;
            font-size: 12px;
            margin-bottom: 10px;
        }

        .card-value {
            font-size: 27px;
            font-weight: 700;
        }

        .card-small {
            color: #727c9b;
            font-size: 11px;
            margin-top: 5px;
        }

        .grid-two {
            display: grid;
            grid-template-columns: 1.7fr 1fr;
            gap: 18px;
        }

        .panel {
            background: rgba(16, 20, 40, 0.92);
            border: 1px solid #222a49;
            border-radius: 17px;
            padding: 20px;
            margin-bottom: 18px;
        }

        .panel-title {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 18px;
        }

        .panel-title h2 {
            font-size: 16px;
        }

        .panel-title span {
            color: #707b9a;
            font-size: 11px;
        }

        .chart-box {
            height: 300px;
        }

        .health {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 300px;
            flex-direction: column;
        }

        .health-ring {
            width: 155px;
            height: 155px;
            border-radius: 50%;
            display: flex;
            justify-content: center;
            align-items: center;
            background:
                conic-gradient(
                    #42e8a7 0deg,
                    #42e8a7 180deg,
                    #26304e 180deg,
                    #26304e 360deg
                );
            position: relative;
        }

        .health-ring::after {
            content: "";
            width: 118px;
            height: 118px;
            border-radius: 50%;
            background: #101428;
            position: absolute;
        }

        .health-content {
            position: relative;
            z-index: 2;
            text-align: center;
        }

        .health-number {
            font-size: 31px;
            font-weight: 700;
        }

        .health-text {
            color: #42e8a7;
            font-size: 12px;
        }

        .actions {
            display: grid;
            grid-template-columns:
                repeat(auto-fit, minmax(190px, 1fr));
            gap: 12px;
        }

        .action-btn {
            border: 1px solid #2b3458;
            background: #12172d;
            color: white;
            padding: 14px;
            border-radius: 12px;
            cursor: pointer;
            transition: 0.2s;
        }

        .action-btn:hover {
            transform: translateY(-2px);
            border-color: #7d6cff;
            background: #171d3b;
        }

        .primary {
            background: #6e5cf6;
            border-color: #6e5cf6;
        }

        .danger {
            background: #351722;
            border-color: #7d293b;
        }

        .table-wrap {
            overflow-x: auto;
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        th,
        td {
            padding: 13px 10px;
            border-bottom: 1px solid #222a45;
            text-align: left;
            font-size: 13px;
        }

        th {
            color: #737e9d;
            font-weight: 500;
        }

        .badge {
            display: inline-block;
            padding: 5px 9px;
            border-radius: 15px;
            font-size: 10px;
        }

        .online {
            color: #42e8a7;
            background: rgba(66, 232, 167, 0.1);
        }

        .high {
            color: #ff6b7a;
            background: rgba(255, 107, 122, 0.1);
        }

        .medium {
            color: #ffc857;
            background: rgba(255, 200, 87, 0.1);
        }

        .resolved {
            color: #42e8a7;
            background: rgba(66, 232, 167, 0.1);
        }

        .small-btn {
            padding: 7px 10px;
            border-radius: 8px;
            border: 1px solid #2b3458;
            background: #151a31;
            color: white;
            cursor: pointer;
            margin-right: 4px;
        }

        .small-btn:hover {
            border-color: #8171ff;
        }

        .search {
            width: 100%;
            background: #0d1124;
            border: 1px solid #2a3353;
            color: white;
            padding: 12px;
            border-radius: 10px;
            margin-bottom: 15px;
            outline: none;
        }

        .form-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }

        .input {
            width: 100%;
            background: #0d1124;
            border: 1px solid #2a3353;
            color: white;
            padding: 12px;
            border-radius: 10px;
            outline: none;
            margin-top: 6px;
        }

        .field {
            margin-bottom: 14px;
        }

        .field label {
            color: #8490b1;
            font-size: 12px;
        }

        .assistant-box {
            max-width: 850px;
            margin: auto;
        }

        .chat {
            min-height: 250px;
            max-height: 450px;
            overflow-y: auto;
            background: #0c1022;
            border: 1px solid #232c4a;
            border-radius: 14px;
            padding: 18px;
            margin-bottom: 14px;
        }

        .message {
            margin-bottom: 13px;
            padding: 12px 14px;
            border-radius: 12px;
            line-height: 1.6;
            font-size: 13px;
        }

        .user-message {
            background: #1c2241;
        }

        .ai-message {
            background: #152b2c;
            border-left: 3px solid #42e8a7;
        }

        .chat-input {
            display: flex;
            gap: 10px;
        }

        .chat-input input {
            flex: 1;
        }

        .report-grid {
            display: grid;
            grid-template-columns:
                repeat(auto-fit, minmax(220px, 1fr));
            gap: 14px;
        }

        .report-item {
            background: #0d1226;
            border: 1px solid #222a47;
            border-radius: 13px;
            padding: 17px;
        }

        .report-item span {
            display: block;
            color: #727c99;
            font-size: 11px;
            margin-bottom: 6px;
        }

        .report-item strong {
            font-size: 22px;
        }

        .modal {
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.72);
            justify-content: center;
            align-items: center;
            z-index: 100;
            padding: 20px;
        }

        .modal-box {
            width: min(500px, 100%);
            background: #11162d;
            border: 1px solid #303a61;
            border-radius: 17px;
            padding: 22px;
        }

        .modal-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 20px;
        }

        .close {
            border: 0;
            background: transparent;
            color: #8992ad;
            font-size: 23px;
            cursor: pointer;
        }

        .qr-image {
            display: block;
            width: 240px;
            height: 240px;
            margin: 15px auto;
            background: white;
            padding: 10px;
            border-radius: 12px;
        }

        .url-box {
            background: #090d1d;
            padding: 12px;
            border-radius: 10px;
            text-align: center;
            word-break: break-all;
            color: #42e8a7;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
        }

        .footer-note {
            color: #5f6986;
            text-align: center;
            font-size: 11px;
            margin-top: 25px;
        }

        @media (max-width: 900px) {

            .sidebar {
                width: 190px;
            }

            .main {
                margin-left: 190px;
                width: calc(100% - 190px);
            }

            .grid-two {
                grid-template-columns: 1fr;
            }
        }

        @media (max-width: 650px) {

            .sidebar {
                position: static;
                width: 100%;
                height: auto;
            }

            .layout {
                display: block;
            }

            .main {
                margin-left: 0;
                width: 100%;
                padding: 16px;
            }

            .form-grid {
                grid-template-columns: 1fr;
            }
        }

    </style>

</head>


<body>


<div class="layout">

    <!-- SIDEBAR -->

    <aside class="sidebar">

        <div class="logo">
            Net<span>Shield</span> AI
        </div>

        <button class="nav-btn active"
                onclick="showSection('dashboard', this)">
            Dashboard
        </button>

        <button class="nav-btn"
                onclick="showSection('devices', this)">
            Devices
        </button>

        <button class="nav-btn"
                onclick="showSection('threats', this)">
            Threat Center
        </button>

        <button class="nav-btn"
                onclick="showSection('assistant', this)">
            AI Assistant
        </button>

        <button class="nav-btn"
                onclick="showSection('reports', this)">
            Reports
        </button>

        <button class="nav-btn"
                onclick="showSection('settings', this)">
            Settings
        </button>

    </aside>


    <!-- MAIN -->

    <main class="main">


        <!-- DASHBOARD -->

        <section id="dashboard"
                 class="section active">

            <div class="topbar">

                <div class="title">

                    <h1>Network Security Dashboard</h1>

                    <p>
                        AI-powered real-time monitoring
                        and threat intelligence
                    </p>

                </div>

                <div class="status">

                    <span class="dot"></span>

                    Monitoring Active

                </div>

            </div>


            <div class="cards">

                <div class="card">

                    <div class="card-label">
                        BANDWIDTH
                    </div>

                    <div class="card-value"
                         id="bandwidth">
                        0
                    </div>

                    <div class="card-small">
                        Mbps
                    </div>

                </div>


                <div class="card">

                    <div class="card-label">
                        PACKETS / SEC
                    </div>

                    <div class="card-value"
                         id="packets">
                        0
                    </div>

                    <div class="card-small">
                        Network packets
                    </div>

                </div>


                <div class="card">

                    <div class="card-label">
                        DEVICES
                    </div>

                    <div class="card-value"
                         id="deviceCount">
                        0
                    </div>

                    <div class="card-small">
                        Online devices
                    </div>

                </div>


                <div class="card">

                    <div class="card-label">
                        ACTIVE THREATS
                    </div>

                    <div class="card-value"
                         id="threatCount">
                        0
                    </div>

                    <div class="card-small">
                        Security alerts
                    </div>

                </div>


                <div class="card">

                    <div class="card-label">
                        AI RISK
                    </div>

                    <div class="card-value"
                         id="risk">
                        0%
                    </div>

                    <div class="card-small">
                        Anomaly risk
                    </div>

                </div>

            </div>


            <div class="grid-two">

                <div class="panel">

                    <div class="panel-title">

                        <h2>
                            Live Network Activity
                        </h2>

                        <span>
                            Auto refresh
                        </span>

                    </div>

                    <div class="chart-box">

                        <canvas id="networkChart"></canvas>

                    </div>

                </div>


                <div class="panel">

                    <div class="panel-title">

                        <h2>
                            Network Health
                        </h2>

                    </div>

                    <div class="health">

                        <div class="health-ring"
                             id="healthRing">

                            <div class="health-content">

                                <div class="health-number"
                                     id="healthNumber">
                                    0%
                                </div>

                                <div class="health-text"
                                     id="healthText">
                                    Excellent
                                </div>

                            </div>

                        </div>

                    </div>

                </div>

            </div>


            <div class="panel">

                <div class="panel-title">

                    <h2>
                        Quick Actions
                    </h2>

                </div>

                <div class="actions">

                    <button class="action-btn primary"
                            onclick="openDeviceModal()">
                        + Add Device
                    </button>

                    <button class="action-btn danger"
                            onclick="simulateThreat()">
                        Run AI Threat Simulation
                    </button>

                    <button class="action-btn"
                            onclick="showQR()">
                        QR Network Access
                    </button>

                    <button class="action-btn"
                            onclick="showSection('reports')">
                        Generate Report
                    </button>

                </div>

            </div>

        </section>


        <!-- DEVICES -->

        <section id="devices"
                 class="section">

            <div class="topbar">

                <div class="title">

                    <h1>Network Devices</h1>

                    <p>
                        Manage connected devices
                    </p>

                </div>

            </div>


            <div class="panel">

                <button class="action-btn primary"
                        onclick="openDeviceModal()"
                        style="margin-bottom:15px;">
                    + Add Device
                </button>

                <input
                    id="deviceSearch"
                    class="search"
                    placeholder="Search device..."
                    oninput="loadDevices()"
                >

                <div class="table-wrap">

                    <table>

                        <thead>

                            <tr>
                                <th>Name</th>
                                <th>IP Address</th>
                                <th>Type</th>
                                <th>Status</th>
                                <th>Risk</th>
                                <th>Actions</th>
                            </tr>

                        </thead>

                        <tbody id="deviceTable">
                        </tbody>

                    </table>

                </div>

            </div>

        </section>


        <!-- THREATS -->

        <section id="threats"
                 class="section">

            <div class="topbar">

                <div class="title">

                    <h1>Threat Center</h1>

                    <p>
                        AI-powered anomaly detection
                    </p>

                </div>

            </div>


            <div class="panel">

                <button class="action-btn danger"
                        onclick="simulateThreat()">
                    Simulate Suspicious Activity
                </button>

            </div>


            <div class="panel">

                <div class="table-wrap">

                    <table>

                        <thead>

                            <tr>
                                <th>Threat</th>
                                <th>Severity</th>
                                <th>Source</th>
                                <th>Time</th>
                                <th>Status</th>
                                <th>Action</th>
                            </tr>

                        </thead>

                        <tbody id="threatTable">
                        </tbody>

                    </table>

                </div>

            </div>

        </section>


        <!-- AI ASSISTANT -->

        <section id="assistant"
                 class="section">

            <div class="topbar">

                <div class="title">

                    <h1>AI Security Assistant</h1>

                    <p>
                        Ask questions about your network
                    </p>

                </div>

            </div>


            <div class="assistant-box">

                <div class="panel">

                    <div class="chat"
                         id="chat">

                        <div class="message ai-message">

                            Hello! I am NetShield AI.
                            Ask me about network health,
                            bandwidth, packets, devices,
                            threats or reports.

                        </div>

                    </div>


                    <div class="chat-input">

                        <input
                            id="aiQuestion"
                            class="input"
                            placeholder="Ask something..."
                            onkeydown="if(event.key === 'Enter') askAI()"
                        >

                        <button class="action-btn primary"
                                onclick="askAI()">
                            Ask AI
                        </button>

                    </div>

                </div>

            </div>

        </section>


        <!-- REPORTS -->

        <section id="reports"
                 class="section">

            <div class="topbar">

                <div class="title">

                    <h1>Security Reports</h1>

                    <p>
                        Current network monitoring report
                    </p>

                </div>

                <button class="action-btn primary"
                        onclick="loadReport()">
                    Refresh Report
                </button>

            </div>


            <div class="panel">

                <div class="report-grid">

                    <div class="report-item">
                        <span>Generated At</span>
                        <strong id="reportTime">-</strong>
                    </div>

                    <div class="report-item">
                        <span>Bandwidth</span>
                        <strong id="reportBandwidth">-</strong>
                    </div>

                    <div class="report-item">
                        <span>Packets / Sec</span>
                        <strong id="reportPackets">-</strong>
                    </div>

                    <div class="report-item">
                        <span>Devices</span>
                        <strong id="reportDevices">-</strong>
                    </div>

                    <div class="report-item">
                        <span>Active Threats</span>
                        <strong id="reportThreats">-</strong>
                    </div>

                    <div class="report-item">
                        <span>AI Risk</span>
                        <strong id="reportRisk">-</strong>
                    </div>

                    <div class="report-item">
                        <span>Health</span>
                        <strong id="reportHealth">-</strong>
                    </div>

                    <div class="report-item">
                        <span>AI Status</span>
                        <strong id="reportAI">-</strong>
                    </div>

                </div>

            </div>

        </section>


        <!-- SETTINGS -->

        <section id="settings"
                 class="section">

            <div class="topbar">

                <div class="title">

                    <h1>Settings</h1>

                    <p>
                        NetShield AI configuration
                    </p>

                </div>

            </div>


            <div class="panel">

                <div class="report-item">

                    <span>Monitoring Status</span>

                    <strong style="color:#42e8a7;">
                        Active
                    </strong>

                </div>

                <br>

                <div class="report-item">

                    <span>AI Engine</span>

                    <strong>
                        """

# Add AI status dynamically to HTML
HTML += "Isolation Forest" if AI_AVAILABLE else "Fallback Detection"

HTML += """
                    </strong>

                </div>

                <br>

                <div class="report-item">

                    <span>Purpose</span>

                    <strong>
                        Network Security Monitoring
                    </strong>

                </div>

                <br>

                <div class="report-item">

                    <span>Simulation Mode</span>

                    <strong id="simulationStatus">
                        OFF
                    </strong>

                </div>

            </div>

        </section>


        <div class="footer-note">
            NetShield AI • AI-Powered Network Security Monitoring System
        </div>

    </main>

</div>


<!-- DEVICE MODAL -->

<div class="modal"
     id="deviceModal">

    <div class="modal-box">

        <div class="modal-header">

            <h2 id="modalTitle">
                Add Device
            </h2>

            <button class="close"
                    onclick="closeDeviceModal()">
                ×
            </button>

        </div>


        <input type="hidden"
               id="editId">


        <div class="field">

            <label>
                Device Name
            </label>

            <input
                id="deviceName"
                class="input"
                placeholder="Example: Office Laptop"
            >

        </div>


        <div class="field">

            <label>
                IP Address
            </label>

            <input
                id="deviceIP"
                class="input"
                placeholder="192.168.1.20"
            >

        </div>


        <div class="field">

            <label>
                Device Type
            </label>

            <select
                id="deviceType"
                class="input">

                <option>Laptop</option>
                <option>Computer</option>
                <option>Router</option>
                <option>Mobile</option>
                <option>Server</option>
                <option>Other</option>

            </select>

        </div>


        <button class="action-btn primary"
                onclick="saveDevice()"
                style="width:100%;">

            Save Device

        </button>

    </div>

</div>


<!-- QR MODAL -->

<div class="modal"
     id="qrModal">

    <div class="modal-box">

        <div class="modal-header">

            <h2>
                QR Network Access
            </h2>

            <button class="close"
                    onclick="closeQR()">
                ×
            </button>

        </div>

        <img
            id="qrImage"
            class="qr-image"
            alt="Network QR Code"
        >

        <div
            id="qrUrl"
            class="url-box">
        </div>

        <p style="
            color:#747e9c;
            text-align:center;
            font-size:11px;
            margin-top:12px;
        ">
            Phone and computer should be connected
            to the same Wi-Fi network.
        </p>

    </div>

</div>


<script>


// =========================================================
// SECTION NAVIGATION
// =========================================================

function showSection(sectionId, button = null) {

    document.querySelectorAll(".section")
        .forEach(section => {
            section.classList.remove("active");
        });

    const section =
        document.getElementById(sectionId);

    if (section) {
        section.classList.add("active");
    }

    document.querySelectorAll(".nav-btn")
        .forEach(btn => {
            btn.classList.remove("active");
        });

    if (button) {
        button.classList.add("active");
    }

    if (sectionId === "threats") {
        loadThreats();
    }

    if (sectionId === "reports") {
        loadReport();
    }
}


// =========================================================
// CHART
// =========================================================

let networkChart = null;

const chartLabels = [];
const chartBandwidth = [];
const chartPackets = [];


function createChart() {

    const canvas =
        document.getElementById("networkChart");

    if (!canvas) {
        return;
    }

    const ctx = canvas.getContext("2d");

    networkChart = new Chart(ctx, {

        type: "line",

        data: {

            labels: chartLabels,

            datasets: [

                {
                    label: "Bandwidth Mbps",
                    data: chartBandwidth,
                    borderWidth: 2,
                    tension: 0.35,
                    fill: false
                },

                {
                    label: "Packets / Sec",
                    data: chartPackets,
                    borderWidth: 2,
                    tension: 0.35,
                    fill: false
                }

            ]

        },

        options: {

            responsive: true,

            maintainAspectRatio: false,

            plugins: {
                legend: {
                    labels: {
                        color: "#9aa4c2"
                    }
                }
            },

            scales: {

                x: {
                    ticks: {
                        color: "#6e7896"
                    },
                    grid: {
                        color: "rgba(100,110,150,0.08)"
                    }
                },

                y: {
                    beginAtZero: true,
                    ticks: {
                        color: "#6e7896"
                    },
                    grid: {
                        color: "rgba(100,110,150,0.08)"
                    }
                }

            }

        }

    });

}


// =========================================================
// DASHBOARD UPDATE
// =========================================================

async function updateDashboard() {

    try {

        const response =
            await fetch("/api/dashboard");

        const data =
            await response.json();


        document.getElementById("bandwidth")
            .textContent =
            data.bandwidth.toFixed(2);


        document.getElementById("packets")
            .textContent =
            data.packets.toFixed(0);


        document.getElementById("deviceCount")
            .textContent =
            data.devices;


        document.getElementById("threatCount")
            .textContent =
            data.threats;


        document.getElementById("risk")
            .textContent =
            data.risk + "%";


        document.getElementById("healthNumber")
            .textContent =
            data.risk + "%";


        document.getElementById("healthText")
            .textContent =
            data.health;


        const simulationStatus =
            document.getElementById("simulationStatus");

        if (simulationStatus) {

            simulationStatus.textContent =
                data.simulation
                    ? "ON"
                    : "OFF";

            simulationStatus.style.color =
                data.simulation
                    ? "#ff6b7a"
                    : "#42e8a7";
        }


        // Health ring
        const safeRisk =
            Math.max(0, Math.min(data.risk, 100));

        const healthy =
            100 - safeRisk;

        const degrees =
            healthy * 3.6;

        document.getElementById("healthRing")
            .style.background =
            `conic-gradient(
                #42e8a7 0deg,
                #42e8a7 ${degrees}deg,
                #26304e ${degrees}deg,
                #26304e 360deg
            )`;


        // Chart
        if (networkChart) {

            const now =
                new Date().toLocaleTimeString();

            chartLabels.push(now);
            chartBandwidth.push(data.bandwidth);
            chartPackets.push(data.packets);

            if (chartLabels.length > 20) {
                chartLabels.shift();
                chartBandwidth.shift();
                chartPackets.shift();
            }

            networkChart.update();
        }


    } catch (error) {

        console.log(
            "Dashboard update error:",
            error
        );

    }

}


// =========================================================
// DEVICES
// =========================================================

async function loadDevices() {

    try {

        const response =
            await fetch("/api/devices");

        const devices =
            await response.json();

        const search =
            document.getElementById("deviceSearch");

        const searchText =
            search
                ? search.value.toLowerCase()
                : "";

        const table =
            document.getElementById("deviceTable");

        table.innerHTML = "";


        devices
            .filter(device => {

                const combined =
                    (
                        device.name +
                        " " +
                        device.ip +
                        " " +
                        device.type
                    ).toLowerCase();

                return combined.includes(searchText);

            })
            .forEach(device => {

                const row =
                    document.createElement("tr");


                const nameCell =
                    document.createElement("td");

                nameCell.textContent =
                    device.name;


                const ipCell =
                    document.createElement("td");

                ipCell.textContent =
                    device.ip;


                const typeCell =
                    document.createElement("td");

                typeCell.textContent =
                    device.type;


                const statusCell =
                    document.createElement("td");

                const statusBadge =
                    document.createElement("span");

                statusBadge.className =
                    "badge online";

                statusBadge.textContent =
                    device.status;

                statusCell.appendChild(
                    statusBadge
                );


                const riskCell =
                    document.createElement("td");

                riskCell.textContent =
                    device.risk + "%";


                const actionCell =
                    document.createElement("td");


                const editButton =
                    document.createElement("button");

                editButton.className =
                    "small-btn";

                editButton.textContent =
                    "Edit";

                editButton.onclick =
                    function () {
                        editDevice(
                            device.id,
                            device.name,
                            device.ip,
                            device.type
                        );
                    };


                const deleteButton =
                    document.createElement("button");

                deleteButton.className =
                    "small-btn";

                deleteButton.textContent =
                    "Delete";

                deleteButton.onclick =
                    function () {
                        deleteDevice(device.id);
                    };


                actionCell.appendChild(
                    editButton
                );

                actionCell.appendChild(
                    deleteButton
                );


                row.appendChild(nameCell);
                row.appendChild(ipCell);
                row.appendChild(typeCell);
                row.appendChild(statusCell);
                row.appendChild(riskCell);
                row.appendChild(actionCell);

                table.appendChild(row);

            });


    } catch (error) {

        console.log(
            "Device loading error:",
            error
        );

    }

}


// =========================================================
// DEVICE MODAL
// =========================================================

function openDeviceModal() {

    document.getElementById("deviceModal")
        .style.display = "flex";

    document.getElementById("modalTitle")
        .textContent = "Add Device";

    document.getElementById("editId")
        .value = "";

    document.getElementById("deviceName")
        .value = "";

    document.getElementById("deviceIP")
        .value = "";

    document.getElementById("deviceType")
        .value = "Computer";
}


function closeDeviceModal() {

    document.getElementById("deviceModal")
        .style.display = "none";
}


function editDevice(
    id,
    name,
    ip,
    type
) {

    document.getElementById("deviceModal")
        .style.display = "flex";

    document.getElementById("modalTitle")
        .textContent = "Edit Device";

    document.getElementById("editId")
        .value = id;

    document.getElementById("deviceName")
        .value = name;

    document.getElementById("deviceIP")
        .value = ip;

    document.getElementById("deviceType")
        .value = type;
}


// =========================================================
// SAVE DEVICE
// =========================================================

async function saveDevice() {

    const id =
        document.getElementById("editId").value;

    const name =
        document.getElementById("deviceName").value.trim();

    const ip =
        document.getElementById("deviceIP").value.trim();

    const type =
        document.getElementById("deviceType").value;


    if (!name || !ip) {

        alert(
            "Please enter device name and IP address."
        );

        return;
    }


    try {

        let response;


        if (id) {

            response =
                await fetch(
                    `/api/devices/edit/${id}`,
                    {
                        method: "PUT",
                        headers: {
                            "Content-Type":
                                "application/json"
                        },
                        body: JSON.stringify({
                            name: name,
                            ip: ip,
                            type: type
                        })
                    }
                );

        } else {

            response =
                await fetch(
                    "/api/devices/add",
                    {
                        method: "POST",
                        headers: {
                            "Content-Type":
                                "application/json"
                        },
                        body: JSON.stringify({
                            name: name,
                            ip: ip,
                            type: type
                        })
                    }
                );

        }


        const result =
            await response.json();


        if (!response.ok) {

            alert(
                result.message ||
                "Something went wrong."
            );

            return;
        }


        closeDeviceModal();

        loadDevices();

        alert(
            id
                ? "Device updated successfully."
                : "Device added successfully."
        );


    } catch (error) {

        alert(
            "Could not connect to the server."
        );

    }

}


// =========================================================
// DELETE DEVICE
// =========================================================

async function deleteDevice(id) {

    const confirmed =
        confirm(
            "Are you sure you want to delete this device?"
        );

    if (!confirmed) {
        return;
    }


    try {

        const response =
            await fetch(
                `/api/devices/delete/${id}`,
                {
                    method: "DELETE"
                }
            );


        const result =
            await response.json();


        if (result.success) {

            loadDevices();

            alert(
                "Device deleted successfully."
            );

        } else {

            alert(
                result.message ||
                "Could not delete device."
            );

        }

    } catch (error) {

        alert(
            "Server connection error."
        );

    }

}


// =========================================================
// THREAT SIMULATION
// =========================================================

async function simulateThreat() {

    try {

        const response =
            await fetch(
                "/api/simulate_threat",
                {
                    method: "POST"
                }
            );


        const result =
            await response.json();


        if (result.success) {

            alert(
                "AI threat simulation started."
            );

            loadThreats();

            updateDashboard();

        }

    } catch (error) {

        alert(
            "Could not start simulation."
        );

    }

}


// =========================================================
// LOAD THREATS
// =========================================================

async function loadThreats() {

    try {

        const response =
            await fetch("/api/threats");

        const threats =
            await response.json();

        const table =
            document.getElementById("threatTable");

        table.innerHTML = "";


        threats
            .slice()
            .reverse()
            .forEach(threat => {

                const row =
                    document.createElement("tr");


                const threatCell =
                    document.createElement("td");

                threatCell.textContent =
                    threat.type;


                const severityCell =
                    document.createElement("td");

                const severity =
                    document.createElement("span");

                severity.className =
                    "badge " +
                    (
                        threat.severity === "Critical" ||
                        threat.severity === "High"
                            ? "high"
                            : "medium"
                    );

                severity.textContent =
                    threat.severity;

                severityCell.appendChild(
                    severity
                );


                const sourceCell =
                    document.createElement("td");

                sourceCell.textContent =
                    threat.source;


                const timeCell =
                    document.createElement("td");

                timeCell.textContent =
                    threat.time;


                const statusCell =
                    document.createElement("td");

                const status =
                    document.createElement("span");

                status.className =
                    "badge " +
                    (
                        threat.status === "Resolved"
                            ? "resolved"
                            : "high"
                    );

                status.textContent =
                    threat.status;

                statusCell.appendChild(
                    status
                );


                const actionCell =
                    document.createElement("td");


                if (threat.status === "Active") {

                    const resolveButton =
                        document.createElement("button");

                    resolveButton.className =
                        "small-btn";

                    resolveButton.textContent =
                        "Resolve";

                    resolveButton.onclick =
                        function () {
                            resolveThreat(
                                threat.id
                            );
                        };

                    actionCell.appendChild(
                        resolveButton
                    );

                } else {

                    actionCell.textContent =
                        "Completed";

                }


                row.appendChild(threatCell);
                row.appendChild(severityCell);
                row.appendChild(sourceCell);
                row.appendChild(timeCell);
                row.appendChild(statusCell);
                row.appendChild(actionCell);

                table.appendChild(row);

            });


    } catch (error) {

        console.log(
            "Threat loading error:",
            error
        );

    }

}


// =========================================================
// RESOLVE THREAT
// =========================================================

async function resolveThreat(id) {

    try {

        const response =
            await fetch(
                `/api/threats/resolve/${id}`,
                {
                    method: "POST"
                }
            );


        const result =
            await response.json();


        if (result.success) {

            loadThreats();

            updateDashboard();

        }

    } catch (error) {

        alert(
            "Could not resolve threat."
        );

    }

}


// =========================================================
// AI ASSISTANT
// =========================================================

async function askAI() {

    const input =
        document.getElementById("aiQuestion");

    const question =
        input.value.trim();


    if (!question) {
        return;
    }


    const chat =
        document.getElementById("chat");


    const userMessage =
        document.createElement("div");

    userMessage.className =
        "message user-message";

    userMessage.textContent =
        "You: " + question;

    chat.appendChild(
        userMessage
    );


    input.value = "";


    try {

        const response =
            await fetch(
                "/api/assistant",
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json"
                    },
                    body: JSON.stringify({
                        question: question
                    })
                }
            );


        const result =
            await response.json();


        const aiMessage =
            document.createElement("div");

        aiMessage.className =
            "message ai-message";

        aiMessage.textContent =
            "NetShield AI: " +
            result.answer;

        chat.appendChild(
            aiMessage
        );


        chat.scrollTop =
            chat.scrollHeight;


    } catch (error) {

        const errorMessage =
            document.createElement("div");

        errorMessage.className =
            "message ai-message";

        errorMessage.textContent =
            "NetShield AI: Server connection error.";

        chat.appendChild(
            errorMessage
        );

    }

}


// =========================================================
// QR CODE
// =========================================================

async function showQR() {

    try {

        const response =
            await fetch("/api/qr");

        const result =
            await response.json();


        if (!result.success) {

            alert(
                result.message ||
                "QR generation failed."
            );

            return;
        }


        document.getElementById("qrImage")
            .src = result.image;


        document.getElementById("qrUrl")
            .textContent = result.url;


        document.getElementById("qrModal")
            .style.display = "flex";


    } catch (error) {

        alert(
            "Could not generate QR code."
        );

    }

}


function closeQR() {

    document.getElementById("qrModal")
        .style.display = "none";
}


// =========================================================
// REPORT
// =========================================================

async function loadReport() {

    try {

        const response =
            await fetch("/api/report");

        const data =
            await response.json();


        document.getElementById("reportTime")
            .textContent =
            data.generated_at;


        document.getElementById("reportBandwidth")
            .textContent =
            data.bandwidth.toFixed(2) +
            " Mbps";


        document.getElementById("reportPackets")
            .textContent =
            data.packets.toFixed(0);


        document.getElementById("reportDevices")
            .textContent =
            data.devices;


        document.getElementById("reportThreats")
            .textContent =
            data.active_threats;


        document.getElementById("reportRisk")
            .textContent =
            data.risk + "%";


        document.getElementById("reportHealth")
            .textContent =
            data.health;


        document.getElementById("reportAI")
            .textContent =
            data.ai_status;


    } catch (error) {

        console.log(
            "Report error:",
            error
        );

    }

}


// =========================================================
// INITIAL STARTUP
// =========================================================

createChart();

updateDashboard();

loadDevices();

loadThreats();

loadReport();


// Update every 2 seconds
setInterval(
    updateDashboard,
    2000
);


// Update threat list every 4 seconds
setInterval(
    loadThreats,
    4000
);


// Update devices every 5 seconds
setInterval(
    loadDevices,
    5000
);


</script>


</body>

</html>
"""


# =========================================================
# HOME ROUTE
# =========================================================

@app.route("/")
def home():
    return render_template_string(HTML)


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":

    initialize_ai()

    local_ip = get_local_ip()

    print()
    print("=" * 60)
    print("             NETSHIELD AI")
    print("=" * 60)
    print()
    print("Local URL : http://127.0.0.1:5000")
    print(f"Network URL: http://{local_ip}:5000")
    print()
    print("Keep this terminal open while using the project.")
    print("Press CTRL+C to stop the server.")
    print()
    print("=" * 60)

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )