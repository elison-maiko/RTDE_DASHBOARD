"""
Tempo real (Socket.IO): leva cada amostra do robô até o navegador.

É aqui que a aquisição (rtde_data_receive) encontra a tela:

    acquisition_loop()  ->  on_new_sample(amostra)
                               1. envia "telemetry" para todos os navegadores
                               2. guarda no histórico dos gráficos
                               3. confere os limites (safety) e, se for o caso, para o robô
                                  -> envia "fault_event"

Eventos enviados ao navegador:
    "telemetry"          cada amostra (static/js/main.js)
    "connection_status"  robô conectado / desconectado
    "fault_event"        limite excedido ou junta em FAULT (popup + Fault History)
    "fault_history"      todos os eventos, ao abrir a página
    "telemetry_history"  últimas amostras, ao abrir a página (gráficos não começam vazios)
"""

import logging
import threading
from collections import deque

from flask_socketio import emit

from safety.alarms import stop_robot

log = logging.getLogger("realtime")

# Campos guardados no histórico dos gráficos (só o que os gráficos usam)
CHART_FIELDS = [
    "temperature", "torque", "current", "joint_positions",
    "main_voltage", "robot_voltage", "robot_current", "avg_power",
]


class Realtime:
    def __init__(self, socketio, robot, alarms, history_size):
        self.socketio = socketio
        self.robot = robot
        self.alarms = alarms

        # Histórico dos gráficos fica no servidor: assim a página pode ser
        # recarregada (ou você pode ir para /config e voltar) sem perder os dados
        self.chart_history = deque(maxlen=history_size)
        self.history_lock = threading.Lock()

        socketio.on_event("connect", self.on_browser_connect)

    def on_browser_connect(self, auth=None):
        """Um navegador abriu a página: manda o estado atual só para ele."""
        emit("connection_status", self.robot.status())
        emit("fault_history", self.alarms.history_list())

        with self.history_lock:
            points = list(self.chart_history)
        emit("telemetry_history", points)

    def on_new_sample(self, sample):
        """Chamado pelo acquisition_loop a cada leitura do robô."""
        # 1. Envia para todos os navegadores abertos
        self.socketio.emit("telemetry", sample)

        # 2. Guarda no histórico dos gráficos
        with self.history_lock:
            self.chart_history.append(make_chart_point(sample))

        # 3. Confere os limites de segurança
        for event in self.alarms.check(sample):
            if event["action"] == "stop":
                stop_robot(self.robot, event)

            log.warning("[%s] %s: %s", event["code"], event["joint"], event["message"])
            self.socketio.emit("fault_event", event)

    def on_connection_change(self):
        """Chamado pelo acquisition_loop quando o robô conecta ou desconecta."""
        self.socketio.emit("connection_status", self.robot.status())


def make_chart_point(sample):
    """Versão reduzida da amostra, com números arredondados (envio mais leve)."""
    point = {"timestamp": sample["timestamp"]}
    for field in CHART_FIELDS:
        point[field] = round_value(sample.get(field))
    return point


def round_value(value):
    if value is None:
        return None
    if isinstance(value, list):
        return [round_value(item) for item in value]
    return round(value, 4)
