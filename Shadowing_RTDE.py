import math
import time
from rtde_receive import RTDEReceiveInterface
from robodk import robolink

# 1. Conexão com o RoboDK
RDK = robolink.Robolink()
robot = RDK.Item('UR10')

if not robot.Valid():
    print("[ERRO] Robô 'UR10' não encontrado no ambiente do RoboDK.")
    exit()

# 2. Configuração de IP e RTDE
IP_UR = "127.0.0.1"

print(f">>> Conectando ao robô via RTDE ({IP_UR})... <<<")

try:
    # A classe RTDEReceiveInterface conecta automaticamente na porta 30004
    rtde_r = RTDEReceiveInterface(IP_UR)
except Exception as e:
    print(f"[ERRO] Falha ao conectar no RTDE: {e}")
    exit()

print(">>> Sombra Digital RTDE Ativa (Modo 60 FPS) <<<")

# 3. Otimização do Motor de Renderização
RDK.Render(False)  # Desativa renderização automática a cada comando

target_fps = 60    # Frequência máxima de atualização visual no RoboDK
render_interval = 1.0 / target_fps
last_render_time = time.time()

# 4. Loop Principal de Espelhamento (Shadowing)
try:
    while rtde_r.isConnected():
        # Obtém os ângulos atuais das juntas em Radianos (Sincronizado via RTDE)
        q_rad = rtde_r.getActualQ()

        if q_rad:
            # Converte radianos para graus
            q_deg = [math.degrees(a) for a in q_rad]

            # Validação de segurança dos ângulos
            if all(-360 <= angle <= 360 for angle in q_deg):
                robot.setJoints(q_deg)

                # Renderização controlada por tempo (evita sobrecarga da GPU)
                current_time = time.time()
                if (current_time - last_render_time) >= render_interval:
                    RDK.Render()
                    last_render_time = current_time

except KeyboardInterrupt:
    print("\n[!] Sombra Digital encerrada pelo usuário.")

finally:
    RDK.Render(True)
    rtde_r.disconnect()
    print("Conexão RTDE finalizada com sucesso.")