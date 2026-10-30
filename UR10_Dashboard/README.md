# UR10 RTDE Dashboard

Dashboard local para monitorar a telemetria do UR10 (URSim no Docker ou robô real)
via RTDE, com limites de segurança configuráveis e alertas em tempo real.

## Páginas

| URL | O que faz |
|---|---|
| `/` | Tela inicial com as duas opções |
| `/monitor` | Telemetria: cards das juntas, energia do robô, gráficos, Fault History (com botão Info), logs CSV |
| `/config` | Limites de corrente, torque e temperatura por junta + ação ao atingir |

## Estrutura

```
UR10_Dashboard/
├── app.py              # Servidor Flask: configuração, páginas, API e Socket.IO
├── robot.py            # Conexão com o robô (RTDE + Dashboard Server) e loop de leitura
├── alarms.py           # Limites (thresholds.json), checagem e histórico de falhas
├── thresholds.json     # Criado ao salvar os limites na página /config
├── templates/
│   ├── base.html       # Partes comuns: <head> e popup de alerta
│   ├── home.html       # Tela inicial
│   ├── monitor.html    # Telemetria
│   └── config.html     # Limites
├── static/
│   ├── style.css       # Todos os estilos (cores no topo, em :root)
│   └── js/
│       ├── socket.js   # Conexão Socket.IO compartilhada
│       ├── alerts.js   # Popup amarelo (alerta) / vermelho (STOP) — todas as páginas
│       ├── home.js     # Status da conexão na tela inicial
│       ├── settings.js # Tabela de limites (/config)
│       ├── main.js     # /monitor: abas, botões Play/Pause/Stop, eventos
│       ├── config.js   # Constantes: cores, métricas, tamanhos de buffer
│       ├── charts.js   # Histórico + gráficos (Chart.js)
│       ├── panels.js   # Status, cards, Fault History + popup Info, TCP pose, energia
│       ├── logs.js     # Gravação de logs CSV
│       └── utils.js    # Helpers de DOM e formatação
├── requirements.txt
└── README.md
```

## Instalação e execução

```powershell
pip install -r requirements.txt

python app.py                                   # URSim local (127.0.0.1)
$env:UR_IP = "192.168.1.10"; python app.py      # robô real
$env:PORT = "5050"; python app.py               # outra porta (padrão 5000)
```

Depois abra **http://localhost:5000**.

## Limites de segurança

- Cada junta tem um limite por métrica; campo vazio = desativado.
- Torque e corrente comparam o valor absoluto (limite de 8 Nm = ±8 Nm).
- Ação por métrica:
  - **Alerta** → popup amarelo + registro no Fault History.
  - **STOP** → envia `stop` ao programa do robô + popup vermelho + registro no Fault History.
- A checagem roda **no servidor** (`alarms.py`), então o STOP funciona mesmo sem
  nenhuma aba do navegador aberta.
- Um evento dispara uma vez ao passar do limite; só volta a disparar depois que o
  valor cai abaixo de 95% do limite (evita repetição por ruído).
- Falhas de junta (modo FAULT 252) também vão para o Fault History.
- O Fault History fica na memória do servidor (últimos 500 eventos) e é perdido
  ao reiniciar o `app.py`.

## Energia do robô e popup Info

- Leituras do RTDE equivalentes à aba *Readings* do PolyScope: tensão principal,
  tensão do robô, corrente do robô e tensão de cada junta.
- O RTDE não envia potência: o `robot.py` calcula `P = tensão do robô × corrente do robô`
  e a **potência média** (média móvel das últimas 50 leituras, ~5 s).
- Aba Home do monitor: um gráfico contínuo (últimos 60 s) com tensão principal, tensão do robô,
  corrente do robô e potência média. Cada unidade tem seu eixo Y (V à esquerda, A e W à direita);
  os botões ao lado mostram o valor atual e ligam/desligam cada parâmetro.
- Cada evento do Fault History guarda uma "foto" do robô naquele instante
  (`SNAPSHOT_FIELDS` em `alarms.py`). O botão **Info** mostra: posição, torque,
  corrente, temperatura e tensão de cada junta, TCP em relação à base (mm / rad) e energia.
- Os logs CSV também incluem as colunas de tensão, corrente e potência.

## Como os dados fluem

```
robot.py poll_loop()  ->  app.py on_sample()
                            ├─ emit "telemetry"   -> main.js (cards, gráficos, logs)
                            └─ alarms.check()     -> se STOP: robot.send_command("stop")
                                 └─ emit "fault_event" -> panels.js (Fault History)
                                                       -> alerts.js (popup)
```

## Onde ajustar

| O quê | Onde |
|---|---|
| IP, porta, frequência (`POLL_HZ`) | topo do `app.py` |
| Nomes das juntas, cores de temperatura dos cards | `FRONTEND_CONFIG` no `app.py` |
| Limites padrão, histerese, tamanho do histórico | topo do `alarms.py` |
| Cores do tema | `:root` no `static/style.css` |
| Cores das juntas, tamanho do histórico dos gráficos | `static/js/config.js` |
| Nova métrica | `robot.py → read()`, `METRICS` em `config.js` e `alarms.py`, `COLUMNS` em `settings.js` |
| Parâmetros do gráfico de energia (cor, unidade), janela de tempo | `POWER_METRICS` / `POWER_WINDOW` em `static/js/config.js` |
| Janela da potência média | `POWER_AVG_SAMPLES` no `robot.py` |
| Dados guardados no popup Info | `SNAPSHOT_FIELDS` no `alarms.py` |

## Observações

- Reconecta automaticamente se o RTDE cair.
- Se o Dashboard Server (porta 29999) falhar, a telemetria continua; os botões
  Play/Pause/Stop e a ação STOP retornam erro (o popup mostra "FALHA ao parar").
- As bibliotecas (Chart.js, Socket.IO) vêm de CDN, então o navegador precisa de internet.
