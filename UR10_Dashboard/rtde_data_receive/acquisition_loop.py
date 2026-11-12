"""
Loop de aquisição: lê o robô em intervalos fixos e entrega cada amostra.

Este arquivo não sabe nada de navegador nem de Flask. Ele recebe duas funções
e chama cada uma no momento certo:

    on_sample(amostra)  -> a cada leitura           (routes/realtime.py)
    on_status()         -> quando a conexão muda    (routes/realtime.py)
"""

import logging
import time

log = logging.getLogger("acquisition")

RETRY_SECONDS = 2  # espera antes de tentar reconectar


def acquisition_loop(robot, hz, on_sample, on_status):
    """Roda para sempre (numa thread separada, iniciada no app.py)."""
    time.sleep(1)  # dá tempo do servidor web subir

    while True:
        # 1. Sem conexão: tenta conectar
        if not robot.is_connected():
            connected = robot.connect()
            on_status()
            if not connected:
                time.sleep(RETRY_SECONDS)
                continue

        # 2. Lê uma amostra
        try:
            sample = robot.read()
        except Exception as error:
            log.error("Erro ao ler os dados do robô: %s", error)
            robot.mark_disconnected(error)
            on_status()
            time.sleep(RETRY_SECONDS)
            continue

        # 3. Entrega a amostra (um erro aqui não pode parar a aquisição)
        try:
            on_sample(sample)
        except Exception:
            log.exception("Erro ao processar a amostra")

        time.sleep(1 / hz)
