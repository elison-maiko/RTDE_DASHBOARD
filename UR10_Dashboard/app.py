"""
UR10 Dashboard — arquivo principal
Responsável por juntar todas as peças
    python app.py                               # URSim local (127.0.0.1)
    IP robô real "192.168.0.10"

Organização das Pastas:
    rtde_data_receive/    conexão com o robô e leitura dos dados (RTDE)
    safety/               limites de segurança e histórico de falhas
    routes/               páginas, API e envio dos dados em tempo real
    dashboard_interface/  HTML, CSS e JavaScript da tela

Caminho de uma leitura:
    acquisition_loop (rtde_data_receive) -> robot.read() -> Realtime.on_new_sample (routes) -> navegador + alarms.check (safety)
"""

import logging
import os
import threading

from flask import Flask
from flask_socketio import SocketIO

from routes.http_routes import register_routes
from routes.realtime import Realtime
from rtde_data_receive.acquisition_loop import acquisition_loop
from rtde_data_receive.robot import Robot
from safety.alarms import Alarms

# ============================================================
# CONFIGURAÇÃO
# ============================================================
UR_IP = os.environ.get("UR_IP", "192.168.0.10")
#IP do Iris Lab 192.168.0.10
#IP do URSIM 127.0.0.1
PORT = int(os.environ.get("PORT", "5001")) # Caso alguma outra aplicação use a 5001, só trocar a porta.
READS_PER_SECOND = 20                      # Trocar a frequência de leitura

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
THRESHOLDS_FILE = os.path.join(BASE_DIR, "thresholds.json")

CHART_HISTORY_SIZE = 3000

JOINT_NAMES = ["J1 (Base)", "J2 (Shoulder)", "J3 (Elbow)",
               "J4 (Wrist 1)", "J5 (Wrist 2)", "J6 (Wrist 3)"]
MODE_RUNNING = 253
MODE_FAULT = 252

# Enviado ao navegador (lido em dashboard_interface/static/js/config.js)
FRONTEND_CONFIG = {
    "jointNames": JOINT_NAMES,
    "modeRunning": MODE_RUNNING,
    "modeFault": MODE_FAULT,
    "tempWarnC": 50,  # card amarelo acima disso
    "tempCritC": 60,  # card vermelho acima disso
}

# ============================================================
# MONTAGEM
# ============================================================
logging.basicConfig(level=logging.INFO, format="[dashboard] %(levelname)s %(name)s: %(message)s")

app = Flask(
    __name__,
    template_folder="dashboard_interface/templates",
    static_folder="dashboard_interface/static",
)
app.config["SECRET_KEY"] = "ur10-dashboard"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

robot = Robot(UR_IP)
alarms = Alarms(THRESHOLDS_FILE, JOINT_NAMES, MODE_FAULT) 

register_routes(app, robot, alarms, UR_IP, FRONTEND_CONFIG)       # routas (HTTP)
realtime = Realtime(socketio, robot, alarms, CHART_HISTORY_SIZE)  # routas (tempo real)

# ============================================================
if __name__ == "__main__":
    # A aquisição roda numa thread separada e entrega cada leitura ao "realtime"
    acquisition = threading.Thread(
        target=acquisition_loop,
        args=(robot, READS_PER_SECOND, realtime.on_new_sample, realtime.on_connection_change),
        daemon=True,
    )
    acquisition.start()

    print(f"UR10 Dashboard -> http://localhost:{PORT}  (robô: {UR_IP})", flush=True)
    socketio.run(app, host="0.0.0.0", port=PORT, debug=False, allow_unsafe_werkzeug=True)
