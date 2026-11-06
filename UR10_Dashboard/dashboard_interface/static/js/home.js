/** Tela inicial: só mostra o status da conexão com o robô. */

import { socket } from './socket.js';
import { byId } from './utils.js';

socket.on('connection_status', ({ connected, ip }) => {
  const pill = byId('conn-pill');
  pill.classList.remove('ok', 'bad', 'wait');
  pill.classList.add(connected ? 'ok' : 'bad');
  byId('conn-label').textContent = connected ? `Robô conectado · ${ip}` : `Robô desconectado · ${ip}`;
});
