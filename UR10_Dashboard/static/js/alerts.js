/**
 * Popup de limite excedido (presente em todas as páginas).
 *   action "alert" -> popup AMARELO  (só aviso)
 *   action "stop"  -> popup VERMELHO (programa foi parado)
 * Vários alertas seguidos entram numa fila e são mostrados um por vez.
 */

import { socket } from './socket.js';
import { byId } from './utils.js';

const STYLES = {
  alert: { icon: '⚠', kicker: 'ALERTA', title: 'Limite excedido' },
  stop:  { icon: '⏹', kicker: 'STOP', title: 'Execução encerrada' },
};

const modal = byId('alert-modal');
const queue = [];

socket.on('fault_event', (event) => {
  if (event.kind !== 'threshold') return;  // falhas de junta só vão para o histórico
  queue.push(event);
  if (!modal.open) showNext();
  else updateQueueInfo();
});

// "Ver Fault History": fecha o popup (o histórico já lista todos os eventos da fila).
// Já no /monitor, só troca de aba — o link para a mesma página não faria nada.
byId('alert-history').addEventListener('click', (e) => {
  queue.length = 0;
  modal.close();
  if (location.pathname === '/monitor') {
    e.preventDefault();
    window.dispatchEvent(new CustomEvent('open-tab', { detail: 'fault' }));
  }
});

byId('alert-ok').addEventListener('click', () => {
  modal.close();
  showNext();
});

// ESC fecha o popup: mostra o próximo da fila
modal.addEventListener('cancel', () => setTimeout(showNext, 0));

function showNext() {
  const event = queue.shift();
  if (!event) return;

  const isStop = event.action === 'stop';
  const style = STYLES[event.action] || STYLES.alert;
  modal.classList.toggle('level-stop', isStop);
  modal.classList.toggle('level-alert', !isStop);

  byId('alert-icon').textContent = style.icon;
  byId('alert-kicker').textContent = `${style.kicker} · ${event.metric.toUpperCase()}`;
  // Se o comando de parada falhou, o título precisa deixar isso claro
  byId('alert-title').textContent = isStop && event.stopped === false ? 'FALHA ao parar o programa' : style.title;
  byId('alert-joint').textContent = event.joint;
  byId('alert-value').textContent = `${event.value.toFixed(2)} ${event.unit}`;
  byId('alert-limit').textContent = event.limit_text;
  byId('alert-message').textContent = event.message;
  byId('alert-time').textContent = new Date(event.time * 1000).toLocaleTimeString();
  updateQueueInfo();

  if (!modal.open) modal.showModal();
}

function updateQueueInfo() {
  const info = byId('alert-queue');
  info.hidden = queue.length === 0;
  info.textContent = `+${queue.length} alerta(s) na fila`;
}
