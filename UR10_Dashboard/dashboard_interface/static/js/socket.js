/**
 * Conexão Socket.IO única, compartilhada por todos os scripts da página.
 *
 * Eventos enviados pelo servidor (routes/realtime.py):
 *   connection_status -> { connected, dashboard_connected, error, ip }
 *   telemetry         -> amostra do robô (rtde_data_receive/robot.py -> read())
 *   fault_history     -> lista de eventos já registrados (ao conectar)
 *   fault_event       -> novo evento: falha de junta ou limite excedido (safety/alarms.py)
 *   telemetry_history -> últimas amostras guardadas no servidor (ao conectar)
 */

if (!window.io) console.error('Biblioteca Socket.IO não foi carregada.');

export const socket = window.io ? window.io() : { on() {} };
