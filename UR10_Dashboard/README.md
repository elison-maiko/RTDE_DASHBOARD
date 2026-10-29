# UR10 RTDE Dashboard

Dashboard local para monitorar a telemetria do UR10 (URSim no Docker ou robô real)
via RTDE, com atualização em tempo real no navegador.

## Estrutura

```
ur10_dashboard/
├── app.py                 # Backend Flask + Socket.IO, lê o RTDE e transmite os dados
├── templates/
│   └── index.html          # Dashboard (HTML/CSS/JS, um único arquivo)
├── requirements.txt
└── README.md
```

## Instalação

No seu venv atual (o mesmo que já usa para `RTDE_DATA.py`):

```powershell
pip install flask flask-socketio ur-rtde
```

## Executando

Por padrão conecta em `127.0.0.1` (URSim). Para apontar para outro IP
(ex.: o robô real na rede), defina a variável de ambiente `UR_IP` antes de rodar:

```powershell
# URSim local (padrão)
python app.py

# Robô real / outro host
$env:UR_IP = "192.168.1.10"
python app.py
```

Depois abra **http://localhost:5000** no navegador. O dashboard:

- Reconecta automaticamente se o RTDE cair (mostra o status "Desconectado" e o erro).
- Atualiza a ~10 Hz (ajustável via `POLL_HZ` em `app.py`).
- Mostra por junta: modo (RUNNING/FAULT/IDLE...), temperatura, torque, corrente,
  e um mini-gráfico de torque das últimas leituras.
- Mostra a pose atual do TCP no rodapé.

## Onde ajustar

- **Frequência de amostragem:** `POLL_HZ` no topo de `app.py`.
- **Limites de alerta de temperatura:** no `index.html`, dentro do listener
  `socket.on('telemetry', ...)` — hoje amarelo acima de 50 °C, vermelho acima de 60 °C.
- **Novas métricas:** adicione a leitura RTDE no `poll_loop()` (em `app.py`) e o
  campo correspondente no `payload`; no `index.html`, adicione o elemento e a
  leitura no handler `telemetry`.
- **Múltiplos clientes:** o Socket.IO já transmite para qualquer número de abas/
  dispositivos na mesma rede — abra `http://<ip-da-sua-maquina>:5000` de outro
  computador na mesma rede para ver o mesmo dashboard.

## Por que Flask-SocketIO em vez de recarregar a página?

O RTDE só permite uma sessão de leitura por conexão de forma eficiente, então o
backend Python mantém a conexão aberta com o robô e empurra os dados para todos
os navegadores conectados via WebSocket — não há polling HTTP nem recriação de
conexão RTDE a cada requisição.
