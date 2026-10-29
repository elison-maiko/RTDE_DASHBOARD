"""
UR10 RTDE Telemetry Dashboard — backend
"""

import os
import time
import threading
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
from rtde_receive import RTDEReceiveInterface
from dashboard_client import DashboardClient

def log(msg):
    print(f"[dashboard] {msg}", flush=True)

IP_UR = os.environ.get("UR_IP", "127.0.0.1")
POLL_HZ = 10

JOINT_NAMES = [
    "J1 (Base)", "J2 (Shoulder)", "J3 (Elbow)",
    "J4 (Wrist 1)", "J5 (Wrist 2)", "J6 (Wrist 3)"
]

JOINT_MODE_MAP = {
    235: "RESET", 236: "SHUTDOWN", 238: "FREEDRIVE", 239: "POWER_OFF",
    245: "NO_RESPONSE", 246: "INIT", 247: "BOOTING", 252: "FAULT",
    253: "RUNNING", 255: "IDLE"
}

app = Flask(__name__)
app.config["SECRET_KEY"] = "ur10-dashboard"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

state = {
    "connected": False,
    "dashboard_connected": False,
    "error": None,
    "ip": IP_UR,
}

rtde_r = None
dashboard_c = None

def connect_rtde():
    global rtde_r, dashboard_c
    log(f"Attempting RTDE & Dashboard connection to {IP_UR} ...")
    t0 = time.time()
    try:
        # 1. Tenta a conexão com a interface RTDE Receive
        if rtde_r is None or not rtde_r.isConnected():
            rtde_r = RTDEReceiveInterface(IP_UR)

        # 2. Tenta a conexão com a interface Dashboard Client
        if dashboard_c is None or not dashboard_c.isConnected():
            dashboard_c = DashboardClient(IP_UR)
            dashboard_c.connect()

        if rtde_r.isConnected():
            state["connected"] = True
            state["dashboard_connected"] = dashboard_c.isConnected() if dashboard_c else False
            state["error"] = None
            log(f"Connected successfully in {time.time() - t0:.2f}s")
            return True
        else:
            raise RuntimeError("RTDE Interface returned isConnected() == False")
    except Exception as exc:
        state["connected"] = False
        state["dashboard_connected"] = False
        state["error"] = str(exc)
        rtde_r = None
        dashboard_c = None
        log(f"Connection FAILED: {exc}")
        return False

def poll_loop():
    global rtde_r
    period = 1.0 / POLL_HZ
    retry_delay = 2.0

    time.sleep(1.0)
    log("Background poll thread active.")

    while True:
        if rtde_r is None or not state["connected"]:
            if connect_rtde():
                socketio.emit("connection_status", state)
            else:
                socketio.emit("connection_status", state)
                time.sleep(retry_delay)
                continue

        try:
            if not rtde_r.isConnected():
                raise RuntimeError("RTDE connection lost")

            joint_modes = rtde_r.getJointMode()
            temperature = rtde_r.getJointTemperatures()
            torque = rtde_r.getTargetMoment()
            current = rtde_r.getActualCurrent()
            tcp_pose = rtde_r.getActualTCPPose()
            joint_positions = rtde_r.getActualQ()

            payload = {
                "timestamp": time.time(),
                "joint_names": JOINT_NAMES,
                "joint_modes": [
                    {"code": int(m), "label": JOINT_MODE_MAP.get(int(m), "UNKNOWN")}
                    for m in joint_modes
                ],
                "temperature": list(temperature),
                "torque": list(torque),
                "current": list(current),
                "joint_positions": list(joint_positions) if joint_positions else None,
                "tcp_pose": list(tcp_pose) if tcp_pose else None,
            }
            socketio.emit("telemetry", payload)

        except Exception as exc:
            log(f"Error while reading telemetry: {exc}")
            state["connected"] = False
            state["error"] = str(exc)
            rtde_r = None
            socketio.emit("connection_status", state)
            time.sleep(retry_delay)
            continue

        time.sleep(period)

@app.route("/")
def index():
    return render_template("index.html", ip=IP_UR)

@app.route("/api/status")
def status():
    return jsonify(state)

# ==========================================
# ROTAS DE CONTROLO DO ROBÔ (Dashboard Client)
# ==========================================

@app.route("/api/control/<action>", methods=["POST"])
def control_action(action):
    global dashboard_c
    if not dashboard_c or not dashboard_c.isConnected():
        # Tenta reconectar o dashboard se estiver desligado
        try:
            dashboard_c = DashboardClient(IP_UR)
            dashboard_c.connect()
        except Exception as e:
            return jsonify({"status": "error", "message": f"Dashboard não conectado: {e}"}), 500

    try:
        if action == "play":
            dashboard_c.play()
        elif action == "pause":
            dashboard_c.pause()
        elif action == "stop":
            dashboard_c.stop()
        else:
            return jsonify({"status": "error", "message": "Ação inválida"}), 400

        log(f"Comando do Dashboard executado: {action}")
        return jsonify({"status": "ok", "action": action})
    except Exception as e:
        log(f"Erro ao executar comando {action}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@socketio.on("connect")
def on_connect():
    log("Browser connected via Socket.IO")
    socketio.emit("connection_status", state)

if __name__ == "__main__":
    t = threading.Thread(target=poll_loop, daemon=True)
    t.start()
    
    print(f"UR10 Dashboard running -> http://localhost:5000 (target robot: {IP_UR})", flush=True)
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, allow_unsafe_werkzeug=True)