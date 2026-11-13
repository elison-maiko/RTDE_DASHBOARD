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
├── app.py                    # Arquivo principal: configuração, junta as peças e liga o servidor
├── thresholds.json           # Limites salvos pela página /config
│
├── rtde_data_receive/        # Conversa com o robô
│   ├── robot.py              #   conexão RTDE + Dashboard Server, read(), play/pause/stop
│   └── acquisition.py        #   loop que lê o robô 10x por segundo e entrega cada amostra
│
├── safety/                   # Regras de segurança
│   └── alarms.py             #   limites, checagem de cada amostra, Fault History, ação STOP
│
├── routes/                   # Ponte entre os dados e o navegador
│   ├── http_routes.py        #   páginas (/, /monitor, /config) e API (/api/...)
│   └── realtime.py           #   Socket.IO: envia cada amostra e os eventos de falha
│
├── dashboard_interface/      # O que roda no navegador
│   ├── templates/
│   │   ├── base.html         #   partes comuns: <head> e popup de alerta
│   │   ├── home.html         #   tela inicial
│   │   ├── monitor.html      #   telemetria
│   │   └── config.html       #   limites
│   └── static/
│       ├── style.css         #   todos os estilos (cores no topo, em :root)
│       └── js/
│           ├── socket.js     #   conexão Socket.IO compartilhada
│           ├── alerts.js     #   popup amarelo (alerta) / vermelho (STOP), todas as páginas
│           ├── home.js       #   status da conexão na tela inicial
│           ├── settings.js   #   tabela de limites (/config)
│           ├── main.js       #   /monitor: abas, botões Play/Pause/Stop, eventos
│           ├── config.js     #   constantes: cores, métricas, tamanhos de buffer
│           ├── charts.js     #   histórico + gráficos (Chart.js)
│           ├── panels.js     #   status, cards, Fault History + popup Info, TCP pose
│           ├── logs.js       #   gravação de logs CSV
│           └── utils.js      #   helpers de DOM e formatação
├── requirements.txt
└── README.md
```

Regra da organização: `rtde_data_receive/` e `safety/` não sabem que existe navegador.
Quem leva os dados para a tela é sempre `routes/`.

## Instalação e execução

```powershell
pip install -r requirements.txt

python app.py                                   # URSim local (127.0.0.1)
$env:UR_IP = "192.168.1.10"; python app.py      # robô real
$env:PORT = "5000"; python app.py               # Ou outra porta (padrão 500X)
```

Depois abra **http://localhost:5000**.

## Limites de segurança

- Cada junta tem um limite por métrica; campo vazio = desativado.
- Torque e corrente comparam o valor absoluto (limite de 8 Nm = ±8 Nm).
- Ação por métrica:
  - **Alerta** → popup amarelo + registro no Fault History.
  - **STOP** → envia `stop` ao programa do robô + popup vermelho + registro no Fault History.
- A checagem roda **no servidor** (`safety/alarms.py`), então o STOP funciona mesmo sem
  nenhuma aba do navegador aberta.
- Um evento dispara uma vez ao passar do limite; só volta a disparar depois que o
  valor cai abaixo de 95% do limite (evita repetição por ruído).
- Falhas de junta (modo FAULT 252) também vão para o Fault History.
- O Fault History fica na memória do servidor (últimos 500 eventos) e é perdido
  ao reiniciar o `app.py`.

## Energia do robô e popup Info

- Leituras do RTDE equivalentes à aba *Readings* do PolyScope: tensão principal,
  tensão do robô, corrente do robô e tensão de cada junta.
- O RTDE não envia potência: o `rtde_data_receive/robot.py` calcula `P = tensão do robô × corrente do robô`
  e a **potência média** (média móvel das últimas 50 leituras).
- Cada evento do Fault History guarda um registro do robô naquele instante
  (`SNAPSHOT_FIELDS` em `safety/alarms.py`). O botão **Info** mostra: posição, torque,
  corrente, temperatura e tensão de cada junta, TCP em relação à base (mm / rad) e energia.
- Os logs CSV também incluem as colunas de tensão, corrente e potência.

## Como os dados fluem

```
rtde_data_receive/acquisition.py   acquisition_loop()   (thread iniciada no app.py)
        │
        ▼
rtde_data_receive/robot.py         robot.read()
        │
        ▼
routes/realtime.py                 Realtime.on_new_sample(amostra)
        ├─ emit "telemetry"         -> main.js (cards, gráficos, logs)
        ├─ guarda no histórico      -> enviado a quem abrir a página ("telemetry_history")
        └─ safety/alarms.py  alarms.check()
```

## Onde ajustar

| O quê | Onde |
|---|---|
| IP, porta, leituras por segundo (`READS_PER_SECOND`) | topo do `app.py` |
| Nomes das juntas, cores de temperatura dos cards | `FRONTEND_CONFIG` no `app.py` |
| Limites padrão, rearme (`RESET_BELOW`), tamanho do Fault History | topo do `safety/alarms.py` |
| Cores do tema | `:root` no `dashboard_interface/static/style.css` |
| Parâmetros do gráfico de energia (cor, unidade), janela de tempo | `POWER_METRICS` / `POWER_WINDOW` em `dashboard_interface/static/js/config.js` |
| Janela da potência média | `POWER_AVERAGE_SIZE` no `rtde_data_receive/robot.py` |
| Dados guardados no popup Info | `SNAPSHOT_FIELDS` no `safety/alarms.py` |

## Observação MASTER

- A gravação de logs CSV fica no navegador: sair da página no meio dela pede confirmação.
- As bibliotecas (Chart.js, Socket.IO) vêm de CDN, então o navegador precisa de internet.

## Observações

- Reconecta automaticamente se o RTDE cair.
- O histórico dos gráficos (últimos ~5 min, `CHART_HISTORY_SIZE` no `app.py`) fica no servidor:
  ao trocar de página ou recarregar, os gráficos voltam com os dados. Só se perde ao reiniciar o `app.py`.
- Se o Dashboard Server (porta 29999) falhar, a telemetria continua;

