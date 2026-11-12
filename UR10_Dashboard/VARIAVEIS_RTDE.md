# Variáveis lidas via RTDE

O dashboard lê **10 variáveis via RTDE**. Todas são lidas na função `read()` de
[`rtde_data_receive/robot.py`](rtde_data_receive/robot.py). Nenhum outro arquivo
do projeto lê dados do robô.

## Por junta (6 valores, um por junta)

| Função ur_rtde           | Variável RTDE          | Chave no dashboard | Unidade                                       |
|--------------------------|------------------------|--------------------|-----------------------------------------------|
| `getJointMode()`         | `joint_mode`           | `joint_modes`      | código → nome (RUNNING, FAULT, ...)           |
| `getActualQ()`           | `actual_q`             | `joint_positions`  | rad                                           |
| `getJointTemperatures()` | `joint_temperatures`   | `temperature`      | °C                                            |
| `getTargetMoment()`      | `target_moment`        | `torque`           | Nm (torque alvo do controlador, não é medido) |
| `getActualCurrent()`     | `actual_current`       | `current`          | A                                             |
| `getActualJointVoltage()`| `actual_joint_voltage` | `joint_voltage`    | V                                             |

## TCP

| Função ur_rtde        | Variável RTDE     | Chave no dashboard | Unidade                             |
|-----------------------|-------------------|--------------------|-------------------------------------|
| `getActualTCPPose()`  | `actual_TCP_pose` | `tcp_pose`         | [x, y, z] em m, [rx, ry, rz] em rad |

## Robô inteiro

| Função ur_rtde            | Variável RTDE          | Chave no dashboard | Unidade                              |
|---------------------------|------------------------|--------------------|--------------------------------------|
| `getActualMainVoltage()`  | `actual_main_voltage`  | `main_voltage`     | V (alimentação da caixa de controle) |
| `getActualRobotVoltage()` | `actual_robot_voltage` | `robot_voltage`    | V (alimentação do braço)             |
| `getActualRobotCurrent()` | `actual_robot_current` | `robot_current`    | A (corrente total do braço)          |

## Valores que não vêm do RTDE

O dashboard envia mais três valores, mas eles são calculados no próprio código:

- `robot_power`: `robot_voltage × robot_current` (W)
- `avg_power`: média das últimas 50 potências (W)
- `timestamp`: horário do PC (`time.time()`), não do robô

## Observação

`RTDEReceiveInterface(ip)` é criado sem lista de variáveis. Assim, a biblioteca
ur_rtde assina todas as variáveis por padrão. O robô envia muito mais dados do
que esses 10, mas o dashboard usa só os listados acima.
