"""
RTDE Telemetry Dashboard — servidor web.

    python app.py                               # URSim local (127.0.0.1)
    $env:UR_IP="192.168.1.10"; python app.py    # robô real

Páginas:  /  (início)   /monitor  (telemetria)   /config  (limites)
"""

import logging
import os
import threading

from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit

from alarms import Alarms
from robot import Robot, poll_loop

# ============================================================
# CONFIGURAÇÃO
# ============================================================
UR_IP = os.environ.get("UR_IP", "127.0.0.1")
PORT = int(os.environ.get("PORT", "5000"))
POLL_HZ = 10          # leituras por segundo
THRESHOLDS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "thresholds.json")

JOINT_NAMES = ["J1 (Base)", "J2 (Shoulder)", "J3 (Elbow)",
               "J4 (Wrist 1)", "J5 (Wrist 2)", "J6 (Wrist 3)"]
MODE_RUNNING = 253
MODE_FAULT = 252

# Enviado ao navegador (lido em static/js/config.js)
FRONTEND_CONFIG = {
    "jointNames": JOINT_NAMES,
    "modeRunning": MODE_RUNNING,
    "modeFault": MODE_FAULT,
    "tempWarnC": 50,  # cor amarela no card acima disso
    "tempCritC": 60,  # cor vermelha no card acima disso
}

# ============================================================
# APP
# ============================================================
logging.basicConfig(level=logging.INFO, format="[dashboard] %(levelname)s %(name)s: %(message)s")

app = Flask(__name__)
app.config["SECRET_KEY"] = "ur10-dashboard"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
robot = Robot(UR_IP)
alarms = Alarms(THRESHOLDS_FILE, JOINT_NAMES, MODE_FAULT)


@app.context_processor
def inject_globals():
    """Variáveis disponíveis em todos os templates."""
    return {"ip": UR_IP, "frontend_config": FRONTEND_CONFIG}


# ============================================================
# PÁGINAS
# ============================================================
@app.route("/")
def home():
    return render_template("home.html")


@app.route("/monitor")
def monitor():
    return render_template("monitor.html")


@app.route("/config")
def config_page():
    return render_template("config.html")


# ============================================================
# API
# ============================================================
@app.route("/api/status")
def status():
    return jsonify(robot.status())


@app.route("/api/control/<action>", methods=["POST"])
def control_action(action):
    """Play / Pause / Stop do programa via Dashboard Server."""
    try:
        robot.send_command(action)
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400
    except Exception as exc:
        logging.error("Erro ao executar comando %s: %s", action, exc)
        return jsonify({"status": "error", "message": str(exc)}), 500
    return jsonify({"status": "ok", "action": action})


@app.route("/api/thresholds", methods=["GET", "POST"])
def thresholds():
    if request.method == "GET":
        return jsonify(alarms.config)
    try:
        alarms.save(request.get_json(force=True))
    except (ValueError, TypeError) as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400
    return jsonify({"status": "ok"})


# ============================================================
# TEMPO REAL
# ============================================================
@socketio.on("connect")
def on_connect():
    # só para quem acabou de conectar
    emit("connection_status", robot.status())
    emit("fault_history", alarms.history_list())


def on_sample(sample):
    """Chamado pelo poll_loop a cada leitura do robô."""
    socketio.emit("telemetry", sample)

    for event in alarms.check(sample):
        if event["action"] == "stop":
            try:
                robot.send_command("stop")
                event["stopped"] = True
                event["message"] += " — programa parado"
            except Exception as exc:
                event["stopped"] = False
                event["message"] += f" — FALHA ao parar: {exc}"
        logging.warning("[%s] %s: %s", event["code"], event["joint"], event["message"])
        socketio.emit("fault_event", event)


def on_status():
    socketio.emit("connection_status", robot.status())


# ============================================================
if __name__ == "__main__":
    threading.Thread(target=poll_loop, args=(robot, POLL_HZ, on_sample, on_status), daemon=True).start()
    print(f"UR10 Dashboard -> http://localhost:{PORT}  (robô: {UR_IP})", flush=True)
    socketio.run(app, host="0.0.0.0", port=PORT, debug=False, allow_unsafe_werkzeug=True)
