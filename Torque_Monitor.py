### Autores:
### Elison Maiko Oliveira de Souza (22102900)
### Italo Miranda Kusmin Alves (22101930)

import os
import time
import math
import numpy as np
import roboticstoolbox as rtb
from collections import deque
from rtde_receive import RTDEReceiveInterface
from robodk import robolink

# 1. Configurações Iniciais
IP_URSIM = "127.0.0.1"

# [Fx, Fy, Fz, Mx, My, Mz]
F_externa = np.array([0.0, 0.0, -100.0, 0.0, 0.0, 0.0])  

# 2. Conexões com RoboDK, RTDE e Motor Cinemático
print(f"Conectando ao URSim no IP {IP_URSIM} e ao RoboDK...")

# Conexão com o RoboDK (Shadowing 3D)
RDK = robolink.Robolink()
robot_3d = RDK.Item('UR10')

if robot_3d.Valid():
    RDK.Render(False)  # Otimiza o renderizador para alta taxa de atualização

# Conexão apenas de LEITURA (RTDE Receive)
rtde_r = RTDEReceiveInterface(IP_URSIM)

# Modelo Matemático (Sem inicializar nenhuma janela externa)
ur10 = rtb.models.UR10()

# 3. Buffer de Log para Terminal (Exibe as últimas 18 linhas lidas)
BUFFER_LINHAS = 18
log_buffer = deque(maxlen=BUFFER_LINHAS)

def exibir_painel_log():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("=" * 95)
    print("      MONITORAMENTO CONTÍNUO DE TORQUE VIA JACOBIANO (UR10 - REAL TIME)      ")
    print("=" * 95)
    print(f" STATUS: Conectado ao robô | Carga Configurada no TCP (N): {F_externa[2]} N (Z)")
    print("-" * 95)
    # Linha 1 do cabeçalho: Nome descritivo da junta
    print(f"{'':<8} | {'Base':<10} {'Shoulder':<10} {'Elbow':<10} {'Wrist 1':<10} {'Wrist 2':<10} {'Wrist 3':<10}")
    # Linha 2 do cabeçalho: Identificador e Unidade
    print(f"{'TEMPO':<8} | {'J1 (Nm)':<10} {'J2 (Nm)':<10} {'J3 (Nm)':<10} {'J4 (Nm)':<10} {'J5 (Nm)':<10} {'J6 (Nm)':<10}")
    print("-" * 95)
    
    for linha in log_buffer:
        print(linha)
        
    print("-" * 95)
    print(" Press [CTRL + C] para encerrar a conexão.")
# 4. Loop Infinito de Monitoramento em Tempo Real
start_time = time.time()
last_display_time = time.time()

print("\n>>> Monitoramento Ativo! Aguardando dados do robô... <<<")

try:
    while rtde_r.isConnected():
        t_now = time.time() - start_time
        
        # A. Leitura da Posição Real das Juntas do Robô (em Radianos)
        pos_atual = rtde_r.getActualQ()
        
        if pos_atual:
            # B. Espelhamento 3D no RoboDK
            if robot_3d.Valid():
                q_deg = [math.degrees(a) for a in pos_atual]
                robot_3d.setJoints(q_deg)
                RDK.Render()

            # C. Cálculo do Jacobiano Transposto e Torques nas Juntas (Tau = J^T * F)
            J = ur10.jacob0(pos_atual)
            torques = J.T @ F_externa
            
            # D. Adiciona a leitura atual ao Buffer de Log
            t_str = "  ".join([f"{t:>9.2f}" for t in torques])
            log_buffer.append(f"{t_now:>6.2f}s  | {t_str}")
            
            # E. Atualiza o Terminal em alta frequência (~10 Hz)
            if time.time() - last_display_time > 0.1:
                exibir_painel_log()
                last_display_time = time.time()

        time.sleep(0.05)  # Frequência de amostragem de ~20 Hz

except KeyboardInterrupt:
    print("\n\n[!] Monitoramento interrompido pelo usuário.")

finally:
    if robot_3d.Valid():
        RDK.Render(True)
    rtde_r.disconnect()
    print("Conexão RTDE encerrada com sucesso.")