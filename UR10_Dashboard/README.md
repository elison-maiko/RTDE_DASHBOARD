# UR10 RTDE Dashboard

Dashboard local para monitorar a telemetria do UR10 (URSim no Docker ou robô real)
via RTDE, com atualização em tempo real no navegador.

## Estrutura

```
UR10_Dashboard/
├── app.py              # Servidor Flask: configuração, rotas HTTP e Socket.IO
├── robot.py            # Conexão com o robô (RTDE + Dashboard Server) e loop de leitura
├── templates/
│   └── index.html      # Estrutura da página (só HTML)
├── static/
│   ├── style.css       # Todos os estilos (cores no topo, em :root)
│   └── js/
│       ├── main.js     # Início: abas, botões Play/Pause/Stop, Socket.IO
│       ├── config.js   # Constantes: cores, métricas, tamanhos de buffer
│       ├── charts.js   # Histórico + gráficos (Chart.js)
│       ├── panels.js   # Status, cards das juntas, falhas, TCP pose
│       ├── logs.js     # Gravação de logs CSV
│       └── utils.js    # Helpers de DOM e formatação
├── requirements.txt
└── README.md
```

## Instalação

```powershell
pip install -r requirements.txt
```

## Executando

```powershell
# URSim local (padrão: 127.0.0.1)
python app.py

# Robô real / outro host
$env:UR_IP = "192.168.1.10"
python app.py

# Outra porta (padrão: 5000)
$env:PORT = "5050"
python app.py
```

Depois abra **http://localhost:5000** no navegador.

## Como os dados fluem

```
robot.py  poll_loop()  --(Socket.IO "telemetry", 10 Hz)-->  main.js  onTelemetry()
                                                              ├─ logs.js    grava CSV
                                                              ├─ charts.js  histórico + gráfico
                                                              └─ panels.js  cards, falhas, pose
```

Os botões Play/Pause/Stop fazem `POST /api/control/<ação>` → `robot.send_command()`.

## Onde ajustar

| O quê | Onde |
|---|---|
| IP, porta, frequência (`POLL_HZ`) | topo do `app.py` |
| Nomes das juntas, limites de temperatura | `FRONTEND_CONFIG` no `app.py` |
| Cores do tema | `:root` no `static/style.css` |
| Cores das juntas, tamanho do histórico | `static/js/config.js` |
| Nova métrica | ler em `robot.py → read()`, adicionar em `METRICS` (`config.js`) e uma aba no `index.html` |

## Observações

- Reconecta automaticamente se o RTDE cair.
- Se o Dashboard Server (porta 29999) falhar, a telemetria continua; só os botões
  Play/Pause/Stop retornam erro.
- Outros computadores na mesma rede podem abrir `http://<ip-da-sua-maquina>:5000`.
- As bibliotecas (Chart.js, Socket.IO) vêm de CDN, então o navegador precisa de internet.
