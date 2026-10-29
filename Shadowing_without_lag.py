import math
import socket
import struct
import time
from robodk import robolink

RDK = robolink.Robolink()
robot = RDK.Item('UR10')

if not robot.Valid():
    print("Robô 'UR10' não encontrado.")
    exit()

HOST = "127.0.0.1"
PORT = 30003

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Otimização TCP: reduz latência eliminando o buffer do protocolo Nagle
s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
s.connect((HOST, PORT))

# Define buffer pequeno para evitar acúmulo de pacotes velhos
s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)

def read_exact(sock, num_bytes):
    buffer = bytearray()
    while len(buffer) < num_bytes:
        packet = sock.recv(num_bytes - len(buffer))
        if not packet:
            return None
        buffer.extend(packet)
    return bytes(buffer)

print(">>> Sombra Digital OTIMIZADA (Modo Ultra Baixa Latência) <<<")

RDK.Render(False)  # Desativa render automático por comando

target_fps = 60    # Limita atualizações visuais a 60 FPS
render_interval = 1.0 / target_fps
last_render_time = time.time()

try:
    while True:
        # --- ESTRATÉGIA ANTI-DELAY: Limpa pacotes acumulados na fila do Socket ---
        # Mantém apenas o último pacote recebido no buffer TCP
        while True:
            try:
                # Tenta ler pacotes acumulados em modo não-bloqueante
                s.setblocking(False)
                peek_data = s.recv(2048, socket.MSG_PEEK)
                if len(peek_data) > 1060:
                    # Se há mais de 1 pacote pendente na fila, descarta o mais antigo
                    header = s.recv(4)
                    pkg_len = struct.unpack('!i', header)[0]
                    s.recv(pkg_len - 4)
                else:
                    break
            except (BlockingIOError, socket.error):
                break
        
        s.setblocking(True)  # Retorna ao modo normal de leitura

        # --- Leitura do Pacote Atual ---
        header = read_exact(s, 4)
        if not header:
            break
            
        packet_len = struct.unpack('!i', header)[0]
        body = read_exact(s, packet_len - 4)
        if not body:
            break
            
        full_packet = header + body

        if len(full_packet) >= 1060:
            q_rad = struct.unpack('!6d', full_packet[252:300])
            q_deg = [math.degrees(a) for a in q_rad]

            if all(-360 <= angle <= 360 for angle in q_deg):
                robot.setJoints(q_deg)

                # Renderização controlada por tempo (FPS Limiter)
                current_time = time.time()
                if (current_time - last_render_time) >= render_interval:
                    RDK.Render()
                    last_render_time = current_time

except KeyboardInterrupt:
    print("\nSombra Digital encerrada pelo usuário.")
finally:
    RDK.Render(True)
    s.close()
