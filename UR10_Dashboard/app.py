"""
UR10 RTDE Telemetry Dashboard — servidor web.

    python app.py                               # URSim local (127.0.0.1)
    $env:UR_IP="192.168.1.10"; python app.py    # robô real
"""

import logging
import os
import threading

from flask import Flask, jsonify, render_template
from flask_socketio import SocketIO, emit

from robot import Robot, poll_loop

# ============================================================
# CONFIGURAÇÃO
# ============================================================
UR_IP = os.environ.get("UR_IP", "127.0.0.1")
PORT = int(os.environ.get("PORT", "5000"))
POLL_HZ = 10          # leituras por segundo

# Enviado ao navegador (lido em static/js/config.js)
FRONTEND_CONFIG = {
    "jointNames": ["J1 (Base)", "J2 (Shoulder)", "J3 (Elbow)",
                   "J4 (Wrist 1)", "J5 (Wrist 2)", "J6 (Wrist 3)"],
    "modeRunning": 253,
    "modeFault": 252,
    "tempWarnC": 50,  # amarelo acima disso
    "tempCritC": 60,  # vermelho acima disso
}

# ============================================================
# APP
# ============================================================
logging.basicConfig(level=logging.INFO, format="[dashboard] %(levelname)s %(name)s: %(message)s")

app = Flask(__name__)
app.config["SECRET_KEY"] = "ur10-dashboard"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
robot = Robot(UR_IP)


# ============================================================
# ROTAS
# ============================================================
@app.route("/")
def index():
    return render_template("index.html", ip=UR_IP, frontend_config=FRONTEND_CONFIG)


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


@socketio.on("connect")
def on_connect():
    emit("connection_status", robot.status())  # só para quem acabou de conectar


# ============================================================
if __name__ == "__main__":
    threading.Thread(target=poll_loop, args=(robot, socketio, POLL_HZ), daemon=True).start()
    print(f"UR10 Dashboard -> http://localhost:{PORT}  (robô: {UR_IP})", flush=True)
    socketio.run(app, host="0.0.0.0", port=PORT, debug=False, allow_unsafe_werkzeug=True)
