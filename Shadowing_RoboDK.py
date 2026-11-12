import math
import socket
import struct
from robodk import robolink

ROBOT_IP = "127.0.0.1"   # URSim. Para o robô físico, troque pelo IP dele
FREQUENCY = 62.5         # Hz - divide certinho o ciclo do CB3 (125) e do e-Series (500)

RDK = robolink.Robolink()
robot = RDK.Item("UR10", robolink.ITEM_TYPE_ROBOT)

if not robot.Valid():
    print("Robô 'UR10' não encontrado.")
    exit()


# Todo pacote RTDE é: tamanho (2 bytes) + tipo (1 letra) + dados
def send(sock, kind, data=b""):
    sock.sendall(struct.pack(">Hc", len(data) + 3, kind) + data)


def read_exact(sock, num_bytes):
    data = b""
    while len(data) < num_bytes:
        packet = sock.recv(num_bytes - len(data))
        if not packet:
            raise ConnectionError("conexão fechada pelo robô")
        data += packet
    return data


# Lê pacotes até chegar a resposta esperada (pula mensagens de texto do robô)
def read_reply(sock, kind):
    while True:
        size, received = struct.unpack(">Hc", read_exact(sock, 3))
        data = read_exact(sock, size - 3)
        if received == kind:
            return data


s = socket.create_connection((ROBOT_IP, 30004), timeout=3)

# Handshake: protocolo versão 2 -> pede só as juntas (actual_q) -> começa a enviar
send(s, b"V", struct.pack(">H", 2))
read_reply(s, b"V")

send(s, b"O", struct.pack(">d", FREQUENCY) + b"actual_q")
if read_reply(s, b"O")[1:] != b"VECTOR6D":
    print("O robô não aceitou a configuração do RTDE.")
    exit()

send(s, b"S")
read_reply(s, b"S")

print(">>> Sombra Digital via RTDE rodando (Ctrl+C para sair) <<<")

RDK.Render(False)  # a tela só atualiza quando a gente mandar
buffer = b""

try:
    while True:
        chunk = s.recv(65536)
        if not chunk:
            print("Conexão encerrada pelo robô.")
            break
        buffer += chunk

        # Se o loop atrasar, chegam vários pacotes de uma vez.
        # Passa por todos e fica só com as juntas do mais recente, assim não acumula delay.
        q_rad = None
        while len(buffer) >= 3:
            size, kind = struct.unpack(">Hc", buffer[:3])
            if len(buffer) < size:
                break  # pacote pela metade, o resto vem no próximo recv
            if kind == b"U":
                q_rad = struct.unpack(">6d", buffer[4:52])  # byte 3 é o id da receita
            buffer = buffer[size:]

        if q_rad:
            robot.setJoints([math.degrees(a) for a in q_rad])
            RDK.Render()

except KeyboardInterrupt:
    print("\nSombra Digital encerrada pelo usuário.")
except OSError as e:
    print(f"\nConexão perdida: {e}")
finally:
    RDK.Render(True)
    s.close()
