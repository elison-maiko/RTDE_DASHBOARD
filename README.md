# TCC Elison

Monitoramento em tempo real de um robô **UR10** (URSim ou robô real) via **RTDE** e Refatoração de codigo gerado via RoboDK
## Estrutura do repositório

| Caminho | O que é |
|---|---|
| [`UR10_Dashboard/`](UR10_Dashboard/) | Dashboard web: telemetria das juntas, gráficos, limites de segurança e alertas |
| [`RoboDK Scripts/`](RoboDK%20Scripts/) | Scripts URScript de paletização gerados no RoboDK |
| [`Shadowing_RoboDK.py`](Shadowing_RoboDK.py) | Shadowing (sombra digital): espelha no RoboDK as juntas do robô em tempo real |
| [`Minimal_RTDE_Monitor.py`](Minimal_RTDE_Monitor.py) | Primeiro protótipo de aquisição RTDE, sem dashboard, no console do terminal |

## Dashboard

O dashboard está na pasta [`UR10_Dashboard/`](UR10_Dashboard/). Ele mostra a telemetria do UR10 no navegador (cards das juntas, energia, gráficos, Fault History, logs CSV) e permite configurar limites de corrente, torque e temperatura com alerta ou STOP.

```bash
cd UR10_Dashboard
pip install -r requirements.txt
python app.py
```

Depois abra http://localhost:5000. Instalação completa, páginas, estrutura e onde ajustar cada coisa estão no [README do dashboard](UR10_Dashboard/README.md).

## Scripts do RoboDK

Os programas de paletização (`Palletizing_Main`) gerados no RoboDK estão na pasta [`RoboDK Scripts/`](RoboDK%20Scripts/):

- `Palletizing_Main_Padrao.script`: saída do pós-processador padrão do RoboDK
- `Palletizing_Main_Pos_processador_editado.script`: saída com o pós-processador editado
- `Elison_TCC_Final.script`: versão final usada no TCC, indicada para uso no UR10

## Shadowing no RoboDK

O código de shadowing está em [`Shadowing_RoboDK.py`](Shadowing_RoboDK.py). Ele se conecta direto na porta RTDE do robô (30004), recebe a posição das juntas (`actual_q`) a 62,5 Hz e atualiza o robô `UR10` da estação aberta no RoboDK, que passa a acompanhar o robô real (ou o URSim) em tempo real.

```bash
pip install robodk
python Shadowing_RoboDK.py
```

O RoboDK precisa estar aberto com um robô chamado `UR10` na estação. O IP fica em `ROBOT_IP` no topo do arquivo (padrão `127.0.0.1`, URSim).

## Minimal RTDE Monitor

[`Minimal_RTDE_Monitor.py`](Minimal_RTDE_Monitor.py) foi o primeiro protótipo de aquisição de dados via RTDE, feito antes do dashboard. Ele roda no console do terminal e mostra, 10 vezes por segundo, uma tabela com o modo, a temperatura, o torque e a corrente de cada junta.

```bash
pip install ur-rtde rich
python Minimal_RTDE_Monitor.py
```

O IP fica em `IP_UR` no topo do arquivo (padrão `127.0.0.1`, URSim).
