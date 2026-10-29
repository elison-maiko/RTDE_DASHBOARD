"""
Comunicação com o UR10.

- RTDE Receive  (porta 30004): leitura de telemetria. Obrigatória.
- Dashboard Server (porta 29999): comandos play/pause/stop. Opcional —
  se falhar, a telemetria continua funcionando.
"""

import logging
import threading
import time

from dashboard_client import DashboardClient
from rtde_receive import RTDEReceiveInterface

log = logging.getLogger("robot")

JOINT_MODE_MAP = {
    235: "RESET", 236: "SHUTDOWN", 238: "FREEDRIVE", 239: "POWER_OFF",
    245: "NO_RESPONSE", 246: "INIT", 247: "BOOTING", 252: "FAULT",
    253: "RUNNING", 255: "IDLE",
}

COMMANDS = ("play", "pause", "stop")


class Robot:
    def __init__(self, ip):
        self.ip = ip
        self.error = None
        self.rtde = None
        self.dashboard = None
        self._lock = threading.Lock()  # o DashboardClient é usado por várias threads HTTP

    # ------------------------------------------------------------- status

    @property
    def connected(self):
        return self.rtde is not None and self.rtde.isConnected()

    def status(self):
        """Estado enviado ao navegador (evento `connection_status` e /api/status)."""
        return {
            "connected": self.connected,
            "dashboard_connected": self.dashboard is not None and self.dashboard.isConnected(),
            "error": self.error,
            "ip": self.ip,
        }

    # ------------------------------------------------------------ conexão

    def connect(self):
        """Conecta RTDE (obrigatório) e Dashboard (opcional). Retorna True se o RTDE conectou."""
        log.info("Conectando ao robô em %s ...", self.ip)
        try:
            if not self.connected:
                self.rtde = RTDEReceiveInterface(self.ip)
            if not self.rtde.isConnected():
                raise RuntimeError("RTDE retornou isConnected() == False")
        except Exception as exc:
            self.rtde, self.error = None, str(exc)
            log.error("Falha na conexão RTDE: %s", exc)
            return False

        self.error = None
        log.info("RTDE conectado")
        self._connect_dashboard()
        return True

    def _connect_dashboard(self):
        with self._lock:
            if self.dashboard is not None and self.dashboard.isConnected():
                return True
            try:
                client = DashboardClient(self.ip)
                client.connect()
                self.dashboard = client
                return True
            except Exception as exc:
                self.dashboard = None
                log.warning("Dashboard Server indisponível: %s", exc)
                return False

    # ----------------------------------------------------------- leitura

    def read(self):
        """Lê uma amostra do RTDE. Para nova métrica: inclua aqui e trate no main.js."""
        r = self.rtde
        tcp_pose = r.getActualTCPPose()
        joint_positions = r.getActualQ()
        return {
            "timestamp": time.time(),
            "joint_modes": [
                {"code": int(m), "label": JOINT_MODE_MAP.get(int(m), "UNKNOWN")}
                for m in r.getJointMode()
            ],
            "temperature": list(r.getJointTemperatures()),  # °C
            "torque": list(r.getTargetMoment()),            # Nm
            "current": list(r.getActualCurrent()),          # A
            "joint_positions": list(joint_positions) if joint_positions else None,  # rad
            "tcp_pose": list(tcp_pose) if tcp_pose else None,  # m / rad
        }

    # ---------------------------------------------------------- comandos

    def send_command(self, action):
        """play / pause / stop. ValueError se inválido, ConnectionError se sem Dashboard."""
        if action not in COMMANDS:
            raise ValueError(f"Ação inválida: {action}")
        if not self._connect_dashboard():
            raise ConnectionError("Dashboard Server não conectado")
        with self._lock:
            getattr(self.dashboard, action)()
        log.info("Comando executado: %s", action)


def poll_loop(robot, socketio, hz, retry_delay=2.0):
    """Loop em segundo plano: lê o RTDE e envia `telemetry` aos navegadores."""
    time.sleep(1.0)
    while True:
        if not robot.connected:
            ok = robot.connect()
            socketio.emit("connection_status", robot.status())
            if not ok:
                time.sleep(retry_delay)
                continue

        try:
            socketio.emit("telemetry", robot.read())
        except Exception as exc:
            log.error("Erro ao ler telemetria: %s", exc)
            robot.rtde, robot.error = None, str(exc)
            socketio.emit("connection_status", robot.status())
            time.sleep(retry_delay)
            continue

        time.sleep(1.0 / hz)
