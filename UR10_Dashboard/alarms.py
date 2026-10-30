"""
Limites (thresholds) de corrente, torque e temperatura + histórico de falhas.

- Os limites ficam salvos em thresholds.json (editados na página /config).
- check() é chamado a cada amostra e retorna os eventos NOVOS:
    * "threshold": uma junta passou do limite de uma métrica
    * "fault":     uma junta entrou em modo FAULT (252)
  Cada evento só dispara na subida (quando passa do limite), não a cada leitura.
"""

import json
import os
import threading
import time
from collections import deque

# chave -> (campo no payload do robot.read(), nome, unidade, compara valor absoluto?)
METRICS = {
    "current":     ("current",     "Corrente",    "A",  True),
    "torque":      ("torque",      "Torque",      "Nm", True),
    "temperature": ("temperature", "Temperatura", "°C", False),
}

ACTIONS = ("alert", "stop")   # alert = só popup | stop = parar programa + popup
HYSTERESIS = 0.05             # volta ao normal só abaixo de 95% do limite (evita repetição)
HISTORY_LEN = 500

# Campos da amostra guardados junto com cada evento (popup Info do Fault History)
SNAPSHOT_FIELDS = (
    "temperature", "torque", "current", "joint_positions", "joint_voltage", "tcp_pose",
    "main_voltage", "robot_voltage", "robot_current", "robot_power", "avg_power",
)


def default_config(joint_count):
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
        self._lock = threading.Lock()
        self._active = set()  # (junta, chave) que estão acima do limite agora
        self.history = deque(maxlen=HISTORY_LEN)
        self.config = self._load()

    # ---------------------------------------------------------- configuração

    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                return self.validate(json.load(f))
        except (OSError, ValueError):
            return default_config(len(self.joint_names))

    def save(self, data):
        """Valida e salva. Lança ValueError se os dados forem inválidos."""
        config = self.validate(data)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        with self._lock:
            self.config = config
            # reavalia os limites com os novos valores (falhas de junta continuam registradas)
            self._active = {k for k in self._active if k[1] == "fault"}

    def validate(self, data):
        n = len(self.joint_names)
        config = {}
        for key in METRICS:
            item = data.get(key) or {}
            action = item.get("action", "alert")
            limits = item.get("limits", [])
            if action not in ACTIONS:
                raise ValueError(f"{key}: ação inválida '{action}'")
            if not isinstance(limits, list) or len(limits) != n:
                raise ValueError(f"{key}: são necessários {n} limites")
            clean = []
            for v in limits:
                if v in (None, ""):
                    clean.append(None)  # vazio = desativado
                    continue
                v = float(v)
                if v <= 0:
                    raise ValueError(f"{key}: limites devem ser positivos")
                clean.append(v)
            config[key] = {"action": action, "limits": clean}
        return config

    # -------------------------------------------------------------- checagem

    def check(self, sample):
        """Compara a amostra com os limites. Retorna a lista de eventos novos."""
        events = []
        with self._lock:
            for i, name in enumerate(self.joint_names):
                # Modo FAULT da junta
                mode = sample["joint_modes"][i]
                in_fault = mode["code"] == self.mode_fault
                if self._rising((i, "fault"), in_fault, not in_fault):
                    events.append(self._event("fault", name, f"FAULT {mode['code']}",
                                              f"Junta em estado de erro: {mode['label']}"))

                # Limites de corrente / torque / temperatura
                for key, (field, label, unit, use_abs) in METRICS.items():
                    limit = self.config[key]["limits"][i]
                    value = sample[field][i]
                    if limit is None or value is None:
                        self._active.discard((i, key))
                        continue
                    v = abs(value) if use_abs else value
                    if self._rising((i, key), v > limit, v < limit * (1 - HYSTERESIS)):
                        limit_text = f"{'±' if use_abs else ''}{limit:g} {unit}"
                        events.append(self._event(
                            "threshold", name, label.upper(),
                            f"{label} de {value:.2f} {unit} ultrapassou o limite de {limit_text}",
                            action=self.config[key]["action"], metric=label, field=field,
                            value=value, unit=unit, limit=limit, limit_text=limit_text,
                        ))

            # "Foto" do robô no momento do evento (botão Info do Fault History)
            if events:
                snapshot = {k: sample.get(k) for k in SNAPSHOT_FIELDS}
                for event in events:
                    event["snapshot"] = snapshot

            self.history.extend(events)
        return events

    def _rising(self, key, above, below):
        """True só no momento em que passa a ficar acima; volta a armar quando fica abaixo."""
        if above and key not in self._active:
            self._active.add(key)
            return True
        if below:
            self._active.discard(key)
        return False

    @staticmethod
    def _event(kind, joint, code, message, **extra):
        return {"time": time.time(), "kind": kind, "joint": joint, "code": code,
                "message": message, "action": None, **extra}

    def history_list(self):
        with self._lock:
            return list(self.history)
