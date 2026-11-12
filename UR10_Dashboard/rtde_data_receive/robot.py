"""
Conexão com o UR10.

Usa duas interfaces da biblioteca ur_rtde:
- RTDE Receive (porta 30004): leitura dos dados. Obrigatória.
- Dashboard Server (porta 29999): comandos play / pause / stop. Opcional,
  se não conectar a leitura continua funcionando.

Como o RTDE funciona: depois de conectado, a própria biblioteca ur_rtde fica
recebendo os dados do robô em segundo plano (125 Hz no CB3, 500 Hz no e-Series).
Cada getAlgumaCoisa() só devolve o último valor que chegou.
"""

import logging
import threading
import time
from collections import deque

from dashboard_client import DashboardClient
from rtde_receive import RTDEReceiveInterface

log = logging.getLogger("robot")

# Código do modo da junta -> nome
JOINT_MODES = {
    235: "RESET",
    236: "SHUTDOWN",
    238: "FREEDRIVE",
    239: "POWER_OFF",
    245: "NO_RESPONSE",
    246: "INIT",
    247: "BOOTING",
    252: "FAULT",
    253: "RUNNING",
    255: "IDLE",
}

# A potência média é a média das últimas 50 leituras (~5 s a 10 Hz)
POWER_AVERAGE_SIZE = 50


class Robot:
    def __init__(self, ip):
        self.ip = ip
        self.rtde = None       # RTDEReceiveInterface
        self.dashboard = None  # DashboardClient
        self.error = None      # última mensagem de erro (mostrada na tela)

        # O Dashboard Server pode receber comandos de várias requisições ao mesmo tempo
        self.dashboard_lock = threading.Lock()

        self.last_powers = deque(maxlen=POWER_AVERAGE_SIZE)

    # ==================================================================
    # Conexão
    # ==================================================================

    def is_connected(self):
        return self.rtde is not None and self.rtde.isConnected()

    def is_dashboard_connected(self):
        return self.dashboard is not None and self.dashboard.isConnected()

    def connect(self):
        """Conecta no RTDE e tenta conectar no Dashboard Server.
        Retorna True se o RTDE conectou."""
        log.info("Conectando ao robô em %s ...", self.ip)

        try:
            self.rtde = RTDEReceiveInterface(self.ip)
        except Exception as error:
            self.mark_disconnected(error)
            log.error("Falha na conexão RTDE: %s", error)
            return False

        if not self.rtde.isConnected():
            self.mark_disconnected("RTDE não conectou")
            log.error("Falha na conexão RTDE")
            return False

        self.error = None
        log.info("RTDE conectado")

        self.connect_dashboard()
        return True

    def connect_dashboard(self):
        """Conecta no Dashboard Server (se ainda não estiver). Retorna True se conectado."""
        with self.dashboard_lock:
            if self.is_dashboard_connected():
                return True

            try:
                client = DashboardClient(self.ip)
                client.connect()
                self.dashboard = client
                return True
            except Exception as error:
                self.dashboard = None
                log.warning("Dashboard Server indisponível: %s", error)
                return False

    def mark_disconnected(self, error):
        """Chamado quando a conexão RTDE cai ou falha."""
        self.rtde = None
        self.error = str(error)

    def status(self):
        """Estado da conexão, enviado para o navegador."""
        return {
            "connected": self.is_connected(),
            "dashboard_connected": self.is_dashboard_connected(),
            "error": self.error,
            "ip": self.ip,
        }

    # ==================================================================
    # Leitura dos dados
    # ==================================================================

    def read(self):
        """Lê uma amostra de todos os dados do robô.

        Este dicionário é exatamente o que chega no navegador (evento "telemetry").
        Para adicionar um dado novo: leia aqui e use no JavaScript.
        """
        r = self.rtde

        # Modo de cada junta (RUNNING, FAULT, ...)
        joint_modes = []
        for code in r.getJointMode():
            code = int(code)
            joint_modes.append({"code": code, "label": JOINT_MODES.get(code, "UNKNOWN")})

        # Posição das juntas e do TCP (podem vir vazias logo após conectar)
        joint_positions = r.getActualQ()
        if not joint_positions:
            joint_positions = None

        tcp_pose = r.getActualTCPPose()
        if not tcp_pose:
            tcp_pose = None

        # Energia (como na aba "Readings" do PolyScope).
        # O RTDE não envia a potência, então calculamos: P = V x I
        robot_voltage = r.getActualRobotVoltage()
        robot_current = r.getActualRobotCurrent()
        power = robot_voltage * robot_current

        self.last_powers.append(power)
        average_power = sum(self.last_powers) / len(self.last_powers)

        return {
            "timestamp": time.time(),
            "joint_modes": joint_modes,

            # Por junta (listas com 6 valores)
            "temperature": list(r.getJointTemperatures()),  # °C
            "torque": list(r.getTargetMoment()),            # Nm (torque alvo do controlador, não medido)
            "current": list(r.getActualCurrent()),          # A
            "joint_voltage": list(r.getActualJointVoltage()),  # V
            "joint_positions": joint_positions,             # rad

            # TCP em relação à base: [x, y, z] em metros, [rx, ry, rz] em rad
            "tcp_pose": tcp_pose,

            # Robô inteiro
            "main_voltage": r.getActualMainVoltage(),  # V, alimentação da caixa de controle
            "robot_voltage": robot_voltage,            # V, alimentação do braço
            "robot_current": robot_current,            # A, corrente total do braço
            "robot_power": power,                      # W, agora
            "avg_power": average_power,                # W, média das últimas leituras
        }

    # ==================================================================
    # Comandos do programa (Dashboard Server)
    # ==================================================================

    def send_command(self, action):
        """Executa "play", "pause" ou "stop" no programa do robô.

        Lança ValueError se a ação não existir e ConnectionError se o
        Dashboard Server não estiver conectado.
        """
        if action not in ("play", "pause", "stop"):
            raise ValueError(f"Ação inválida: {action}")

        if not self.connect_dashboard():
            raise ConnectionError("Dashboard Server não conectado")

        with self.dashboard_lock:
            if action == "play":
                self.dashboard.play()
            elif action == "pause":
                self.dashboard.pause()
            else:
                self.dashboard.stop()

        log.info("Comando executado: %s", action)
