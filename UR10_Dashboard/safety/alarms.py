"""
Limites de segurança: corrente, torque e temperatura de cada junta.

- Os limites são editados na página /config e salvos em thresholds.json.
- check() é chamado a cada amostra e devolve só os eventos NOVOS:
    "threshold" -> uma junta passou do limite de corrente, torque ou temperatura
    "fault"     -> uma junta entrou em modo FAULT (252)
- Um evento dispara uma vez, quando o valor passa do limite. Só volta a
  disparar depois que o valor cai abaixo de 95% do limite.
- Ação de cada métrica: "alert" (só popup) ou "stop" (para o programa + popup).
"""

import json
import logging
import threading
import time
from collections import deque

log = logging.getLogger("alarms")

# Métricas que podem ter limite. A chave é o mesmo nome do campo na amostra (robot.read()).
# use_abs = compara o valor sem sinal (torque de -45 Nm também passa de um limite de 40 Nm)
METRICS = {
    "current":     {"label": "Corrente",    "unit": "A",  "use_abs": True},
    "torque":      {"label": "Torque",      "unit": "Nm", "use_abs": True},
    "temperature": {"label": "Temperatura", "unit": "°C", "use_abs": False},
}

ACTIONS = ("alert", "stop")
RESET_BELOW = 0.95   # o alarme "rearma" quando o valor cai abaixo de 95% do limite
HISTORY_SIZE = 500   # quantos eventos o Fault History guarda

# Dados da amostra guardados junto com cada evento (popup "Info" do Fault History)
SNAPSHOT_FIELDS = [
    "temperature", "torque", "current", "joint_positions", "joint_voltage", "tcp_pose",
    "main_voltage", "robot_voltage", "robot_current", "robot_power", "avg_power",
]


def default_config(joint_count):
    """Limites usados quando ainda não existe thresholds.json."""
    return {
        "current":     {"action": "alert", "limits": [None] * joint_count},
        "torque":      {"action": "alert", "limits": [None] * joint_count},
        "temperature": {"action": "alert", "limits": [60.0] * joint_count},
    }


class Alarms:
    def __init__(self, path, joint_names, mode_fault):
        self.path = path
        self.joint_names = joint_names
        self.mode_fault = mode_fault

        # Alarmes que estão disparados agora, ex: (1, "torque") = J2 acima do limite de torque
        self.active = set()

        self.history = deque(maxlen=HISTORY_SIZE)
        self.lock = threading.Lock()  # check() e save() rodam em threads diferentes
        self.config = self.load()

    # ==================================================================
    # Configuração (thresholds.json)
    # ==================================================================

    def load(self):
        try:
            with open(self.path, encoding="utf-8") as file:
                return self.validate(json.load(file))
        except (OSError, ValueError):
            return default_config(len(self.joint_names))

    def save(self, data):
        """Valida e salva os limites vindos da página /config.
        Lança ValueError se algum valor for inválido."""
        config = self.validate(data)

        with open(self.path, "w", encoding="utf-8") as file:
            json.dump(config, file, indent=2)

        with self.lock:
            self.config = config
            # Com limites novos, os alarmes de limite começam do zero.
            # Os alarmes de FAULT continuam como estão.
            for alarm in list(self.active):
                if alarm[1] != "fault":
                    self.active.remove(alarm)

    def validate(self, data):
        """Confere o formato dos limites e devolve uma versão limpa."""
        joint_count = len(self.joint_names)
        config = {}

        for metric in METRICS:
            item = data.get(metric) or {}
            action = item.get("action", "alert")
            limits = item.get("limits", [])

            if action not in ACTIONS:
                raise ValueError(f"{metric}: ação inválida '{action}'")
            if not isinstance(limits, list) or len(limits) != joint_count:
                raise ValueError(f"{metric}: são necessários {joint_count} limites")

            clean_limits = []
            for value in limits:
                if value is None or value == "":
                    clean_limits.append(None)  # campo vazio = limite desligado
                    continue
                value = float(value)
                if value <= 0:
                    raise ValueError(f"{metric}: os limites devem ser positivos")
                clean_limits.append(value)

            config[metric] = {"action": action, "limits": clean_limits}

        return config

    # ==================================================================
    # Checagem de cada amostra
    # ==================================================================

    def check(self, sample):
        """Compara a amostra com os limites. Devolve a lista de eventos novos."""
        new_events = []

        with self.lock:
            for joint in range(len(self.joint_names)):
                event = self.check_joint_fault(joint, sample)
                if event:
                    new_events.append(event)

                for metric in METRICS:
                    event = self.check_limit(joint, metric, sample)
                    if event:
                        new_events.append(event)

            # Guarda uma "foto" do robô neste instante em cada evento
            if new_events:
                snapshot = {}
                for field in SNAPSHOT_FIELDS:
                    snapshot[field] = sample.get(field)
                for event in new_events:
                    event["snapshot"] = snapshot

            self.history.extend(new_events)

        return new_events

    def check_joint_fault(self, joint, sample):
        """Evento quando a junta entra em modo FAULT."""
        mode = sample["joint_modes"][joint]
        alarm = (joint, "fault")

        if mode["code"] != self.mode_fault:
            self.active.discard(alarm)  # saiu do FAULT
            return None

        if alarm in self.active:
            return None  # já estava em FAULT, já foi registrado

        self.active.add(alarm)
        return self.new_event(
            kind="fault",
            joint=joint,
            code=f"FAULT {mode['code']}",
            message=f"Junta em estado de erro: {mode['label']}",
        )

    def check_limit(self, joint, metric, sample):
        """Evento quando a junta passa do limite de uma métrica."""
        limit = self.config[metric]["limits"][joint]
        value = sample[metric][joint]
        alarm = (joint, metric)

        if limit is None or value is None:
            self.active.discard(alarm)  # limite desligado
            return None

        info = METRICS[metric]
        if info["use_abs"]:
            compared = abs(value)
        else:
            compared = value

        # Alarme já disparado: espera o valor baixar para rearmar
        if alarm in self.active:
            if compared < limit * RESET_BELOW:
                self.active.remove(alarm)
            return None

        if compared <= limit:
            return None  # tudo normal

        # Passou do limite agora
        self.active.add(alarm)

        unit = info["unit"]
        if info["use_abs"]:
            limit_text = f"±{limit:g} {unit}"
        else:
            limit_text = f"{limit:g} {unit}"

        event = self.new_event(
            kind="threshold",
            joint=joint,
            code=info["label"].upper(),
            message=f"{info['label']} de {value:.2f} {unit} ultrapassou o limite de {limit_text}",
        )
        event["action"] = self.config[metric]["action"]
        event["metric"] = info["label"]
        event["field"] = metric
        event["value"] = value
        event["unit"] = unit
        event["limit"] = limit
        event["limit_text"] = limit_text
        return event

    def new_event(self, kind, joint, code, message):
        return {
            "time": time.time(),
            "kind": kind,
            "joint": self.joint_names[joint],
            "code": code,
            "message": message,
            "action": None,
        }

    def history_list(self):
        with self.lock:
            return list(self.history)


def stop_robot(robot, event):
    """Executa a ação STOP de um evento e anota no evento se deu certo."""
    try:
        robot.send_command("stop")
        event["stopped"] = True
        event["message"] += " — programa parado"
    except Exception as error:
        event["stopped"] = False
        event["message"] += f" — FALHA ao parar: {error}"
        log.error("Não foi possível parar o programa: %s", error)
