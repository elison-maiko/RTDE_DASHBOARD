/**
 * Conexão Socket.IO única, compartilhada por todos os scripts da página.
 *
 * Eventos enviados pelo servidor (app.py):
 *   connection_status -> { connected, dashboard_connected, error, ip }
 *   telemetry         -> amostra do robô (robot.py -> read())
 *   fault_history     -> lista de eventos já registrados (ao conectar)
 *   fault_event       -> novo evento: falha de junta ou limite excedido (alarms.py)
 */

if (!window.io) console.error('Biblioteca Socket.IO não foi carregada.');

export const socket = window.io ? window.io() : { on() {} };
