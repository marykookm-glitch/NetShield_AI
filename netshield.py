from flask import Flask, jsonify, request, render_template_string
import psutil
import socket
import time
import random
import io
import base64
from datetime import datetime

try:
    from sklearn.ensemble import IsolationForest
    AI_AVAILABLE = True
except Exception:
    AI_AVAILABLE = False

try:
    import qrcode
    QR_AVAILABLE = True
except Exception:
    QR_AVAILABLE = False


app = Flask(__name__)

# =========================================================
# NETSHIELD AI
# AI-Powered Real-Time Network Intelligence
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


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()

        if ip.startswith("127."):
            return "127.0.0.1"

        return ip

    except Exception:
        return "127.0.0.1"


def get_network_data():

    global previous_net
    global previous_time

    current_net = psutil.net_io_counters()
    current_time = time.time()

    time_diff = current_time - previous_time

    if time_diff <= 0:
        time_diff = 1

    sent_delta = current_net.bytes_sent - previous_net.bytes_sent
    recv_delta = current_net.bytes_recv - previous_net.bytes_recv

    packet_delta = (
        (current_net.packets_sent - previous_net.packets_sent)
        +
        (current_net.packets_recv - previous_net.packets_recv)
    )

    total_bytes = sent_delta + recv_delta

    mbps = (total_bytes * 8) / time_diff / 1_000_000

    packets_per_second = packet_delta / time_diff

    previous_net = current_net
    previous_time = current_time

    connections = 0

    try:
        connections = len(psutil.net_connections(kind="inet"))
    except Exception:
        connections = random.randint(8, 25)

    if simulation_mode:
        mbps += random.uniform(15, 45)
        packets_per_second += random.uniform(100, 500)
        connections += random.randint(10, 30)

    return {
        "mbps": round(mbps, 2),
        "packets": round(packets_per_second, 2),
        "connections": connections,
        "sent": current_net.bytes_sent,
        "received": current_net.bytes_recv
    }


def calculate_ai_risk(data):

    mbps = data["mbps"]
    packets = data["packets"]

    # Normalized network features
    feature1 = min(mbps / 100, 10)
    feature2 = min(packets / 1000, 10)

    if AI_AVAILABLE:

        try:

            normal_data = []

            for _ in range(100):
                normal_data.append([
                    random.uniform(0.01, 2.5),
                    random.uniform(1, 150)
                ])

            model = IsolationForest(
                contamination=0.08,
                random_state=42
            )

            model.fit(normal_data)

            prediction = model.predict([
                [feature1, feature2]
            ])[0]

            if prediction == -1:

                risk = random.randint(65, 92)

            else:

                risk = random.randint(5, 25)

        except Exception:

            risk = min(
                100,
                int(feature1 * 10 + feature2 * 3)
            )

    else:

        risk = min(
            100,
            int(feature1 * 10 + feature2 * 3)
        )

    if simulation_mode:
        risk = max(risk, random.randint(70, 95))

    return risk


def get_health(risk):

    if risk < 30:
        return "Excellent"

    if risk < 55:
        return "Good"

    if risk < 75:
        return "Warning"

    return "Critical"


def create_qr():

    if not QR_AVAILABLE:
        return None

    ip = get_local_ip()

    url = f"http://{ip}:5000"

    try:

        qr = qrcode.QRCode(
            version=1,
            box_size=8,
            border=3
        )

        qr.add_data(url)
        qr.make(fit=True)

        image = qr.make_image()

        buffer = io.BytesIO()

        image.save(buffer, format="PNG")

        encoded = base64.b64encode(
            buffer.getvalue()
        ).decode()

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

    active_threats = len([
        t for t in threats
        if t["status"] == "Active"
    ])

    result = {
        "network": data,
        "risk": risk,
        "health": health,
        "devices": len(devices),
        "active_threats": active_threats,
        "time": datetime.now().strftime("%H:%M:%S")
    }

    history.append({
        "time": result["time"],
        "mbps": data["mbps"],
        "risk": risk
    })

    if len(history) > 30:
        history.pop(0)

    return jsonify(result)


@app.route("/api/history")
def get_history():

    return jsonify(history)


# =========================================================
# DEVICE MANAGEMENT
# =========================================================

@app.route("/api/devices")
def get_devices():

    return jsonify(devices)


@app.route("/api/devices/add", methods=["POST"])
def add_device():

    data = request.json

    new_id = max(
        [d["id"] for d in devices],
        default=0
    ) + 1

    device = {
        "id": new_id,
        "name": data.get("name", "Unknown Device"),
        "ip": data.get("ip", "0.0.0.0"),
        "type": data.get("type", "Computer"),
        "status": "Online",
        "risk": random.randint(5, 25)
    }

    devices.append(device)

    return jsonify({
        "success": True,
        "device": device
    })


@app.route("/api/devices/edit/<int:device_id>", methods=["PUT"])
def edit_device(device_id):

    data = request.json

    for device in devices:

        if device["id"] == device_id:

            device["name"] = data.get(
                "name",
                device["name"]
            )

            device["ip"] = data.get(
                "ip",
                device["ip"]
            )

            device["type"] = data.get(
                "type",
                device["type"]
            )

            return jsonify({
                "success": True,
                "device": device
            })

    return jsonify({
        "success": False,
        "message": "Device not found"
    })


@app.route("/api/devices/delete/<int:device_id>", methods=["DELETE"])
def delete_device(device_id):

    global devices

    devices = [
        d for d in devices
        if d["id"] != device_id
    ]

    return jsonify({
        "success": True
    })


# =========================================================
# THREAT CENTER
# =========================================================

@app.route("/api/simulate_threat", methods=["POST"])
def simulate_threat():

    global simulation_mode

    simulation_mode = True

    threat_id = len(threats) + 1

    threat = {
        "id": threat_id,
        "type": random.choice([
            "Abnormal Traffic",
            "Suspicious Activity",
            "Bandwidth Spike",
            "Unknown Device Behavior"
        ]),
        "severity": random.choice([
            "Medium",
            "High",
            "Critical"
        ]),
        "source": random.choice([
            "192.168.1.25",
            "192.168.1.30",
            "192.168.1.45"
        ]),
        "time": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "status": "Active"
    }

    threats.insert(0, threat)

    return jsonify({
        "success": True,
        "threat": threat
    })


@app.route("/api/threats")
def get_threats():

    return jsonify(threats)


@app.route("/api/threats/resolve/<int:threat_id>", methods=["POST"])
def resolve_threat(threat_id):

    for threat in threats:

        if threat["id"] == threat_id:

            threat["status"] = "Resolved"

            return jsonify({
                "success": True
            })

    return jsonify({
        "success": False
    })


# =========================================================
# AI ASSISTANT
# =========================================================

@app.route("/api/assistant", methods=["POST"])
def assistant():

    data = request.json

    question = data.get(
        "question",
        ""
    ).lower()

    network = get_network_data()

    risk = calculate_ai_risk(network)

    if "slow" in question:

        answer = (
            f"AI Analysis: Current network speed is "
            f"{network['mbps']} Mbps. "
            f"Check active connections and bandwidth-heavy devices."
        )

    elif "threat" in question:

        answer = (
            f"AI Analysis: There are "
            f"{len(threats)} detected threat records. "
            f"Current AI risk score is {risk}/100."
        )

    elif "device" in question:

        answer = (
            f"Network currently contains "
            f"{len(devices)} managed devices."
        )

    elif "health" in question:

        answer = (
            f"Network health is currently "
            f"{get_health(risk)} with an AI risk score "
            f"of {risk}/100."
        )

    elif "bandwidth" in question:

        answer = (
            f"Current bandwidth activity is "
            f"{network['mbps']} Mbps."
        )

    elif "report" in question:

        answer = (
            f"Report summary: {len(devices)} devices, "
            f"{len(threats)} threats and current risk "
            f"{risk}/100."
        )

    else:

        answer = (
            "I can analyze network health, bandwidth, "
            "devices, threats and risk. "
            "Try asking: 'network health', "
            "'any threats?', or 'show bandwidth'."
        )

    return jsonify({
        "answer": answer
    })


# =========================================================
# QR ACCESS
# =========================================================

@app.route("/api/qr")
def qr_access():

    qr = create_qr()

    if qr is None:

        return jsonify({
            "success": False,
            "message": "QR package unavailable"
        })

    return jsonify({
        "success": True,
        "url": qr["url"],
        "image": qr["image"]
    })


# =========================================================
# REPORT
# =========================================================

@app.route("/api/report")
def report():

    network = get_network_data()

    risk = calculate_ai_risk(network)

    return jsonify({
        "generated_at":
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        "devices":
            len(devices),
        "threats":
            len(threats),
        "active_threats":
            len([
                t for t in threats
                if t["status"] == "Active"
            ]),
        "network_speed":
            network["mbps"],
        "packets_per_second":
            network["packets"],
        "connections":
            network["connections"],
        "risk":
            risk,
        "health":
            get_health(risk)
    })


# =========================================================
# MAIN HTML
# =========================================================

HTML = r"""
<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width, initial-scale=1.0">

<title>NetShield AI</title>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<link rel="preconnect"
href="https://fonts.googleapis.com">

<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Poppins:wght@400;500;600;700&display=swap"
rel="stylesheet">

<style>

*{
    box-sizing:border-box;
    margin:0;
    padding:0;
}

body{

    font-family:Poppins,sans-serif;

    background:
    radial-gradient(
        circle at top right,
        #1d1740,
        #070914 45%,
        #04050a
    );

    color:#f4f7ff;

    min-height:100vh;
}

.sidebar{

    position:fixed;

    left:0;
    top:0;

    width:240px;
    height:100vh;

    background:rgba(10,12,25,.95);

    border-right:1px solid rgba(120,90,255,.25);

    padding:25px 15px;

    z-index:10;
}

.logo{

    font-size:23px;

    font-weight:700;

    margin-bottom:35px;

    padding-left:10px;

    color:#9d8cff;
}

.logo span{

    color:#25e6ff;
}

.nav button{

    width:100%;

    background:transparent;

    border:0;

    color:#9da4bd;

    padding:14px;

    margin:4px 0;

    border-radius:12px;

    text-align:left;

    font-size:14px;

    cursor:pointer;

    transition:.25s;
}

.nav button:hover,
.nav button.active{

    background:linear-gradient(
        90deg,
        rgba(111,75,255,.35),
        rgba(32,217,255,.08)
    );

    color:white;

    box-shadow:
    0 0 20px rgba(120,80,255,.15);
}

.main{

    margin-left:240px;

    padding:25px;

}

.topbar{

    display:flex;

    justify-content:space-between;

    align-items:center;

    margin-bottom:25px;
}

.title h1{

    font-size:27px;
}

.title p{

    color:#858da8;

    font-size:13px;

    margin-top:5px;
}

.live{

    display:flex;

    align-items:center;

    gap:8px;

    font-size:12px;

    color:#6df7ae;
}

.dot{

    width:9px;
    height:9px;

    border-radius:50%;

    background:#39f58c;

    box-shadow:0 0 12px #39f58c;
}

.cards{

    display:grid;

    grid-template-columns:
    repeat(5,1fr);

    gap:15px;

    margin-bottom:20px;
}

.card{

    background:rgba(16,19,38,.78);

    border:1px solid
    rgba(130,110,255,.16);

    border-radius:18px;

    padding:20px;

    backdrop-filter:blur(12px);

    transition:.25s;
}

.card:hover{

    transform:translateY(-3px);

    border-color:
    rgba(127,107,255,.5);

    box-shadow:
    0 10px 35px rgba(0,0,0,.3);
}

.card-label{

    font-size:12px;

    color:#8c94ad;

    margin-bottom:9px;
}

.card-value{

    font-size:25px;

    font-weight:700;
}

.blue{
    color:#38dfff;
}

.purple{
    color:#a78bfa;
}

.green{
    color:#5cf3a1;
}

.red{
    color:#ff637c;
}

.yellow{
    color:#ffd166;
}

.grid{

    display:grid;

    grid-template-columns:
    2fr 1fr;

    gap:18px;

    margin-bottom:20px;
}

.panel{

    background:rgba(13,17,34,.85);

    border:
    1px solid rgba(130,110,255,.16);

    border-radius:18px;

    padding:20px;
}

.panel-head{

    display:flex;

    justify-content:space-between;

    align-items:center;

    margin-bottom:15px;
}

.panel h2{

    font-size:16px;
}

.small{

    color:#8089a6;

    font-size:11px;
}

canvas{

    max-height:300px;
}

.health{

    text-align:center;

    padding:20px 0;
}

.health-ring{

    width:150px;
    height:150px;

    border-radius:50%;

    margin:0 auto 15px;

    display:flex;

    align-items:center;

    justify-content:center;

    background:
    radial-gradient(
        circle,
        #111528 55%,
        transparent 57%
    );

    border:8px solid #42efa0;

    box-shadow:
    0 0 30px rgba(66,239,160,.2);
}

.health-ring span{

    font-size:27px;

    font-weight:700;
}

.btn{

    border:0;

    border-radius:10px;

    padding:10px 15px;

    color:white;

    cursor:pointer;

    font-family:Poppins;

    font-size:12px;

    transition:.2s;
}

.btn:hover{

    transform:translateY(-2px);

}

.btn-primary{

    background:
    linear-gradient(
        135deg,
        #7657ff,
        #21b9ff
    );

}

.btn-danger{

    background:
    linear-gradient(
        135deg,
        #ff416c,
        #ff4b2b
    );

}

.btn-green{

    background:
    linear-gradient(
        135deg,
        #10b981,
        #06b6d4
    );

}

.btn-dark{

    background:#1a1e35;

    border:1px solid #2b3150;
}

.table-wrap{

    overflow-x:auto;
}

table{

    width:100%;

    border-collapse:collapse;

    font-size:12px;
}

th{

    text-align:left;

    color:#707994;

    padding:12px;

    border-bottom:
    1px solid #242943;
}

td{

    padding:14px 12px;

    border-bottom:
    1px solid #181c30;
}

.badge{

    display:inline-block;

    padding:5px 9px;

    border-radius:20px;

    font-size:10px;

    background:#17223a;

}

.online{

    color:#62f5a6;
}

.risk-low{

    color:#62f5a6;
}

.risk-high{

    color:#ff657c;
}

.action-btn{

    border:0;

    background:#181d35;

    color:#aeb6d0;

    padding:6px 9px;

    border-radius:7px;

    cursor:pointer;

    margin-right:4px;
}

.action-btn:hover{

    color:white;

}

.search{

    background:#10142a;

    border:1px solid #252b48;

    border-radius:10px;

    padding:10px 12px;

    color:white;

    outline:none;

    width:220px;
}

.modal{

    position:fixed;

    inset:0;

    background:rgba(0,0,0,.7);

    display:none;

    align-items:center;

    justify-content:center;

    z-index:50;
}

.modal-box{

    width:420px;

    max-width:90%;

    background:#10142a;

    border:1px solid #333a62;

    border-radius:18px;

    padding:25px;
}

.modal-box h2{

    margin-bottom:20px;
}

.input{

    width:100%;

    background:#080b18;

    border:1px solid #2a3151;

    color:white;

    border-radius:9px;

    padding:11px;

    margin-bottom:12px;

    outline:none;
}

.assistant{

    display:flex;

    gap:10px;

    margin-top:15px;
}

.assistant input{

    flex:1;

    background:#080b18;

    border:1px solid #292f4c;

    color:white;

    padding:11px;

    border-radius:9px;

    outline:none;
}

.ai-answer{

    margin-top:15px;

    padding:14px;

    border-radius:10px;

    background:#0a1021;

    border:1px solid #252d4c;

    color:#b9c1d8;

    font-size:12px;

    line-height:1.7;
}

.qr-box{

    text-align:center;

    padding:10px;
}

.qr-box img{

    width:220px;

    background:white;

    padding:10px;

    border-radius:12px;
}

.section{

    display:none;
}

.section.active{

    display:block;
}

.alert{

    padding:12px;

    border-radius:10px;

    margin-bottom:8px;

    background:#171b31;

    border-left:3px solid #ff657c;
}

@media(max-width:1000px){

    .cards{

        grid-template-columns:
        repeat(2,1fr);
    }

    .grid{

        grid-template-columns:1fr;
    }

}

@media(max-width:700px){

    .sidebar{

        width:70px;
    }

    .logo{

        font-size:0;
    }

    .logo span{

        font-size:20px;
    }

    .nav button{

        font-size:0;
        text-align:center;
    }

    .nav button::first-letter{

        font-size:18px;
    }

    .main{

        margin-left:70px;

        padding:15px;
    }

    .cards{

        grid-template-columns:1fr;
    }

}

</style>

</head>


<body>


<div class="sidebar">

    <div class="logo">
        NETSHIELD <span>AI</span>
    </div>

    <div class="nav">

        <button
        class="active"
        onclick="showSection('dashboard',this)">
        ◈ Dashboard
        </button>

        <button
        onclick="showSection('devices',this)">
        ◉ Devices
        </button>

        <button
        onclick="showSection('threats',this)">
        ⚠ Threat Center
        </button>

        <button
        onclick="showSection('assistant',this)">
        ✦ AI Assistant
        </button>

        <button
        onclick="showSection('reports',this)">
        ▣ Reports
        </button>

        <button
        onclick="showSection('settings',this)">
        ⚙ Settings
        </button>

    </div>

</div>


<div class="main">


<div class="topbar">

    <div class="title">

        <h1>
            Network Intelligence Center
        </h1>

        <p>
            AI-powered real-time network monitoring
        </p>

    </div>

    <div class="live">

        <div class="dot"></div>

        LIVE MONITORING

    </div>

</div>


<!-- =====================================================
DASHBOARD
===================================================== -->

<div
id="dashboard"
class="section active">


<div class="cards">

    <div class="card">

        <div class="card-label">
            BANDWIDTH
        </div>

        <div
        class="card-value blue"
        id="bandwidth">
        0 Mbps
        </div>

    </div>


    <div class="card">

        <div class="card-label">
            PACKETS / SEC
        </div>

        <div
        class="card-value purple"
        id="packets">
        0
        </div>

    </div>


    <div class="card">

        <div class="card-label">
            DEVICES
        </div>

        <div
        class="card-value green"
        id="deviceCount">
        0
        </div>

    </div>


    <div class="card">

        <div class="card-label">
            ACTIVE THREATS
        </div>

        <div
        class="card-value red"
        id="threatCount">
        0
        </div>

    </div>


    <div class="card">

        <div class="card-label">
            AI RISK SCORE
        </div>

        <div
        class="card-value yellow"
        id="risk">
        0/100
        </div>

    </div>

</div>


<div class="grid">


<div class="panel">

    <div class="panel-head">

        <h2>
            Live Network Activity
        </h2>

        <span
        class="small"
        id="updateTime">
        updating...
        </span>

    </div>

    <canvas id="networkChart"></canvas>

</div>


<div class="panel">

    <div class="panel-head">

        <h2>
            Network Health
        </h2>

    </div>

    <div class="health">

        <div
        class="health-ring"
        id="healthRing">

            <span id="healthScore">
                0
            </span>

        </div>

        <h3 id="healthText">
            Checking...
        </h3>

        <p class="small">
            AI-based network risk analysis
        </p>

    </div>

</div>

</div>


<div class="panel">

    <div class="panel-head">

        <h2>
            Quick Actions
        </h2>

        <span class="small">
            Safe demonstration controls
        </span>

    </div>

    <button
    class="btn btn-primary"
    onclick="openDeviceModal()">
        + Add Device
    </button>

    <button
    class="btn btn-danger"
    onclick="simulateThreat()">
        ⚠ Run AI Threat Simulation
    </button>

    <button
    class="btn btn-green"
    onclick="showQR()">
        ◉ QR Access
    </button>

</div>


</div>


<!-- =====================================================
DEVICES
===================================================== -->

<div
id="devices"
class="section">

<div class="panel">

    <div class="panel-head">

        <h2>
            Device Management
        </h2>

        <div>

            <input
            class="search"
            id="deviceSearch"
            placeholder="Search device..."
            onkeyup="loadDevices()">

            <button
            class="btn btn-primary"
            onclick="openDeviceModal()">
            + Add Device
            </button>

        </div>

    </div>


    <div class="table-wrap">

    <table>

        <thead>

            <tr>

                <th>ID</th>
                <th>DEVICE</th>
                <th>IP ADDRESS</th>
                <th>TYPE</th>
                <th>STATUS</th>
                <th>RISK</th>
                <th>ACTIONS</th>

            </tr>

        </thead>

        <tbody
        id="deviceTable">
        </tbody>

    </table>

    </div>

</div>

</div>


<!-- =====================================================
THREATS
===================================================== -->

<div
id="threats"
class="section">

<div class="panel">

    <div class="panel-head">

        <h2>
            AI Threat Center
        </h2>

        <button
        class="btn btn-danger"
        onclick="simulateThreat()">
        + Simulate Safe Threat
        </button>

    </div>

    <div id="threatList">

        <p class="small">
            No threat records yet.
        </p>

    </div>

</div>

</div>


<!-- =====================================================
AI ASSISTANT
===================================================== -->

<div
id="assistant"
class="section">

<div class="panel">

    <h2>
        ✦ NetShield AI Assistant
    </h2>

    <p
    class="small"
    style="margin-top:6px">

        Ask about network health,
        bandwidth, devices or threats.

    </p>


    <div class="assistant">

        <input
        id="aiQuestion"
        placeholder="Example: Is my network healthy?">

        <button
        class="btn btn-primary"
        onclick="askAI()">
        Ask AI
        </button>

    </div>


    <div
    class="ai-answer"
    id="aiAnswer">

        AI Assistant is ready.

    </div>

</div>

</div>


<!-- =====================================================
REPORTS
===================================================== -->

<div
id="reports"
class="section">

<div class="panel">

    <div class="panel-head">

        <h2>
            Network Report
        </h2>

        <button
        class="btn btn-primary"
        onclick="loadReport()">
        Generate Report
        </button>

    </div>

    <div id="reportBox">

        <p class="small">
            Click Generate Report.
        </p>

    </div>

</div>

</div>


<!-- =====================================================
SETTINGS
===================================================== -->

<div
id="settings"
class="section">

<div class="panel">

    <h2>
        Settings
    </h2>

    <br>

    <p class="small">
        Monitoring Status
    </p>

    <br>

    <button
    class="btn btn-green"
    onclick="alert('Real-time monitoring is active.')">

        ● Monitoring Active

    </button>

    <br><br>

    <p class="small">

        NetShield AI is designed for
        authorized networks only.

    </p>

</div>

</div>


</div>


<!-- =====================================================
DEVICE MODAL
===================================================== -->

<div
class="modal"
id="deviceModal">

<div class="modal-box">

    <h2 id="modalTitle">
        Add Device
    </h2>

    <input
    class="input"
    id="deviceName"
    placeholder="Device name">

    <input
    class="input"
    id="deviceIP"
    placeholder="IP address">

    <input
    class="input"
    id="deviceType"
    placeholder="Device type">

    <input
    type="hidden"
    id="editId">

    <button
    class="btn btn-primary"
    onclick="saveDevice()">
    Save Device
    </button>

    <button
    class="btn btn-dark"
    onclick="closeDeviceModal()">
    Cancel
    </button>

</div>

</div>


<!-- =====================================================
QR MODAL
===================================================== -->

<div
class="modal"
id="qrModal">

<div class="modal-box qr-box">

    <h2>
        Scan to Access NetShield AI
    </h2>

    <br>

    <img
    id="qrImage"
    src="">

    <br><br>

    <p
    class="small"
    id="qrURL">
    </p>

    <br>

    <button
    class="btn btn-dark"
    onclick="closeQR()">
    Close
    </button>

</div>

</div>


<script>

let chart;

let labels = [];

let bandwidthData = [];


// =====================================================
// SECTION NAVIGATION
// =====================================================

function showSection(id,button){

    document
    .querySelectorAll(".section")
    .forEach(
        s => s.classList.remove("active")
    );

    document
    .getElementById(id)
    .classList.add("active");


    document
    .querySelectorAll(".nav button")
    .forEach(
        b => b.classList.remove("active")
    );

    button.classList.add("active");


    if(id === "devices"){
        loadDevices();
    }

    if(id === "threats"){
        loadThreats();
    }

}


// =====================================================
// CHART
// =====================================================

function createChart(){

    const ctx =
    document
    .getElementById("networkChart")
    .getContext("2d");


    chart = new Chart(
        ctx,
        {
            type:"line",

            data:{
                labels:labels,

                datasets:[

                    {
                        label:"Bandwidth Mbps",

                        data:bandwidthData,

                        borderColor:"#38dfff",

                        backgroundColor:
                        "rgba(56,223,255,.08)",

                        fill:true,

                        tension:.4
                    }

                ]
            },

            options:{

                responsive:true,

                plugins:{
                    legend:{
                        labels:{
                            color:"#9ca5c2"
                        }
                    }
                },

                scales:{

                    x:{
                        ticks:{
                            color:"#737d9b"
                        },

                        grid:{
                            color:
                            "rgba(255,255,255,.04)"
                        }
                    },

                    y:{
                        ticks:{
                            color:"#737d9b"
                        },

                        grid:{
                            color:
                            "rgba(255,255,255,.04)"
                        }
                    }

                }

            }
        }
    );

}


// =====================================================
// DASHBOARD UPDATE
// =====================================================

async function updateDashboard(){

    try{

        const response =
        await fetch(
            "/api/dashboard"
        );

        const data =
        await response.json();


        document
        .getElementById("bandwidth")
        .innerText =
        data.network.mbps +
        " Mbps";


        document
        .getElementById("packets")
        .innerText =
        Math.round(
            data.network.packets
        );


        document
        .getElementById("deviceCount")
        .innerText =
        data.devices;


        document
        .getElementById("threatCount")
        .innerText =
        data.active_threats;


        document
        .getElementById("risk")
        .innerText =
        data.risk +
        "/100";


        document
        .getElementById("healthScore")
        .innerText =
        100 - data.risk;


        document
        .getElementById("healthText")
        .innerText =
        data.health;


        document
        .getElementById("updateTime")
        .innerText =
        "Updated " +
        data.time;


        labels.push(
            data.time
        );

        bandwidthData.push(
            data.network.mbps
        );


        if(labels.length > 20){

            labels.shift();
            bandwidthData.shift();

        }


        if(chart){

            chart.data.labels =
            labels;

            chart.data.datasets[0].data =
            bandwidthData;

            chart.update();

        }

    }
    catch(error){

        console.log(error);

    }

}


// =====================================================
// DEVICE LOAD
// =====================================================

async function loadDevices(){

    const response =
    await fetch(
        "/api/devices"
    );

    const devices =
    await response.json();


    const search =
    document
    .getElementById("deviceSearch")
    ?.value
    .toLowerCase() || "";


    const table =
    document
    .getElementById("deviceTable");


    table.innerHTML = "";


    devices

    .filter(
        d =>
        d.name.toLowerCase()
        .includes(search)
        ||
        d.ip.toLowerCase()
        .includes(search)
    )

    .forEach(d => {

        const row =
        document.createElement("tr");


        row.innerHTML = `

            <td>${d.id}</td>

            <td>${d.name}</td>

            <td>
                ${d.ip}
            </td>

            <td>
                <span class="badge">
                    ${d.type}
                </span>
            </td>

            <td class="online">
                ● ${d.status}
            </td>

            <td class="${
                d.risk > 50
                ? 'risk-high'
                : 'risk-low'
            }">

                ${d.risk}%

            </td>

            <td>

                <button
                class="action-btn"
                onclick="editDevice(
                    ${d.id},
                    '${escapeText(d.name)}',
                    '${escapeText(d.ip)}',
                    '${escapeText(d.type)}'
                )">

                    Edit

                </button>

                <button
                class="action-btn"
                onclick="deleteDevice(${d.id})">

                    Delete

                </button>

            </td>

        `;

        table.appendChild(row);

    });

}


function escapeText(text){

    return text
    .replace(/'/g,"\\'")
    .replace(/"/g,'&quot;');

}


// =====================================================
// DEVICE MODAL
// =====================================================

function openDeviceModal(){

    document
    .getElementById("modalTitle")
    .innerText =
    "Add Device";


    document
    .getElementById("deviceName")
    .value = "";


    document
    .getElementById("deviceIP")
    .value = "";


    document
    .getElementById("deviceType")
    .value = "";


    document
    .getElementById("editId")
    .value = "";


    document
    .getElementById("deviceModal")
    .style.display =
    "flex";

}


function closeDeviceModal(){

    document
    .getElementById("deviceModal")
    .style.display =
    "none";

}


function editDevice(
    id,
    name,
    ip,
    type
){

    document
    .getElementById("modalTitle")
    .innerText =
    "Edit Device";


    document
    .getElementById("deviceName")
    .value =
    name;


    document
    .getElementById("deviceIP")
    .value =
    ip;


    document
    .getElementById("deviceType")
    .value =
    type;


    document
    .getElementById("editId")
    .value =
    id;


    document
    .getElementById("deviceModal")
    .style.display =
    "flex";

}


async function saveDevice(){

    const name =
    document
    .getElementById("deviceName")
    .value;

    const ip =
    document
    .getElementById("deviceIP")
    .value;

    const type =
    document
    .getElementById("deviceType")
    .value;

    const editId =
    document
    .getElementById("editId")
    .value;


    if(!name || !ip){

        alert(
            "Please enter device name and IP."
        );

        return;
    }


    if(editId){

        await fetch(
            "/api/devices/edit/" +
            editId,
            {
                method:"PUT",

                headers:{
                    "Content-Type":
                    "application/json"
                },

                body:JSON.stringify({
                    name:name,
                    ip:ip,
                    type:type
                })
            }
        );

    }
    else{

        await fetch(
            "/api/devices/add",
            {
                method:"POST",

                headers:{
                    "Content-Type":
                    "application/json"
                },

                body:JSON.stringify({
                    name:name,
                    ip:ip,
                    type:type
                })
            }
        );

    }


    closeDeviceModal();

    loadDevices();

    updateDashboard();

}


// =====================================================
// DELETE DEVICE
// =====================================================

async function deleteDevice(id){

    if(
        !confirm(
            "Delete this device?"
        )
    ){

        return;

    }


    await fetch(
        "/api/devices/delete/" +
        id,
        {
            method:"DELETE"
        }
    );


    loadDevices();

    updateDashboard();

}


// =====================================================
// THREAT SIMULATION
// =====================================================

async function simulateThreat(){

    await fetch(
        "/api/simulate_threat",
        {
            method:"POST"
        }
    );


    alert(
        "AI threat simulation created successfully."
    );


    updateDashboard();

    loadThreats();

}


// =====================================================
// LOAD THREATS
// =====================================================

async function loadThreats(){

    const response =
    await fetch(
        "/api/threats"
    );

    const threats =
    await response.json();


    const list =
    document
    .getElementById("threatList");


    list.innerHTML = "";


    if(threats.length === 0){

        list.innerHTML =
        `
        <p class="small">
            No threats detected.
        </p>
        `;

        return;

    }


    threats.forEach(
        threat => {

            const div =
            document.createElement("div");


            div.className =
            "alert";


            div.innerHTML = `

                <strong>
                    ${threat.type}
                </strong>

                <br>

                <span class="small">

                    Severity:
                    ${threat.severity}

                    |
                    Source:
                    ${threat.source}

                    |
                    ${threat.time}

                </span>

                <br><br>

                <span class="badge">
                    ${threat.status}
                </span>

                ${
                    threat.status === "Active"
                    ?
                    `
                    <button
                    class="btn btn-green"
                    style="margin-left:10px"
                    onclick="resolveThreat(
                        ${threat.id}
                    )">

                        Resolve

                    </button>
                    `
                    :
                    ""
                }

            `;


            list.appendChild(div);

        }
    );

}


// =====================================================
// RESOLVE THREAT
// =====================================================

async function resolveThreat(id){

    await fetch(
        "/api/threats/resolve/" +
        id,
        {
            method:"POST"
        }
    );


    loadThreats();

    updateDashboard();

}


// =====================================================
// AI ASSISTANT
// =====================================================

async function askAI(){

    const question =
    document
    .getElementById("aiQuestion")
    .value;


    if(!question){

        alert(
            "Please enter a question."
        );

        return;

    }


    const response =
    await fetch(
        "/api/assistant",
        {
            method:"POST",

            headers:{
                "Content-Type":
                "application/json"
            },

            body:JSON.stringify({
                question:question
            })
        }
    );


    const data =
    await response.json();


    document
    .getElementById("aiAnswer")
    .innerText =
    data.answer;

}


// =====================================================
// QR ACCESS
// =====================================================

async function showQR(){

    const response =
    await fetch(
        "/api/qr"
    );


    const data =
    await response.json();


    if(!data.success){

        alert(
            "QR generation failed."
        );

        return;

    }


    document
    .getElementById("qrImage")
    .src =
    data.image;


    document
    .getElementById("qrURL")
    .innerText =
    data.url;


    document
    .getElementById("qrModal")
    .style.display =
    "flex";

}


function closeQR(){

    document
    .getElementById("qrModal")
    .style.display =
    "none";

}


// =====================================================
// REPORT
// =====================================================

async function loadReport(){

    const response =
    await fetch(
        "/api/report"
    );


    const data =
    await response.json();


    document
    .getElementById("reportBox")
    .innerHTML = `

        <div class="cards">

            <div class="card">
                <div class="card-label">
                    DEVICES
                </div>

                <div class="card-value green">
                    ${data.devices}
                </div>
            </div>

            <div class="card">
                <div class="card-label">
                    THREATS
                </div>

                <div class="card-value red">
                    ${data.threats}
                </div>
            </div>

            <div class="card">
                <div class="card-label">
                    NETWORK
                </div>

                <div class="card-value blue">
                    ${data.network_speed}
                    Mbps
                </div>
            </div>

            <div class="card">
                <div class="card-label">
                    AI RISK
                </div>

                <div class="card-value yellow">
                    ${data.risk}/100
                </div>
            </div>

        </div>

        <p class="small">
            Generated:
            ${data.generated_at}
        </p>

        <br>

        <p>
            Network Health:
            <strong>
                ${data.health}
            </strong>
        </p>

        <br>

        <p>
            Active Threats:
            ${data.active_threats}
        </p>

        <br>

        <p>
            Active Connections:
            ${data.connections}
        </p>

    `;

}


// =====================================================
// START
// =====================================================

createChart();

updateDashboard();

loadDevices();

setInterval(
    updateDashboard,
    2000
);

</script>


</body>

</html>
"""


# =========================================================
# FLASK ROUTE
# =========================================================

@app.route("/")
def home():

    return render_template_string(
        HTML
    )


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("       NETSHIELD AI")
    print("       AI-Powered Network Intelligence")
    print("=" * 60)
    print()
    print(
        "Local URL : http://127.0.0.1:5000"
    )
    print(
        "LAN URL   : http://" +
        get_local_ip() +
        ":5000"
    )
    print()
    print("Press CTRL+C to stop server.")
    print("=" * 60)
    print()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )