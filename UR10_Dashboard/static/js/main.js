/**
 * Ponto de entrada do frontend: abas, botões do robô e conexão Socket.IO.
 *
 * Fluxo: backend emite "telemetry" -> onTelemetry() -> logs, histórico, cards, gráfico.
 *
 * Arquivos:
 *   config.js  constantes (nomes, cores, métricas)
 *   utils.js   helpers de DOM e formatação
 *   charts.js  histórico + gráficos (Chart.js)
 *   panels.js  status, cards, falhas, TCP pose
 *   logs.js    gravação CSV
 */

import { METRICS } from './config.js';
import { history, initMainChart, isPaused, refreshMainChart, showMetric } from './charts.js';
import { initLogs, recordSample } from './logs.js';
import { initJointCards, recordFaults, setConnection, updateJointCards, updateRate, updateTcpPose } from './panels.js';
import { byId, radToDeg } from './utils.js';

let activeTab = 'home';
const isMetricTab = (tab) => tab in METRICS;

// ============================================================
// TELEMETRIA
// ============================================================
function onTelemetry(sample) {
  const positionsDeg = sample.joint_positions?.map(radToDeg) ?? null;

  recordSample(sample, positionsDeg);   // grava mesmo pausado
  if (isPaused()) return;

  setConnection(true);
  updateRate(sample.timestamp);
  history.push(sample, positionsDeg);

  updateJointCards(sample);
  recordFaults(sample);
  updateTcpPose(sample.tcp_pose);
  if (isMetricTab(activeTab)) refreshMainChart();
}

// ============================================================
// ABAS
// ============================================================
function initTabs() {
  const buttons = document.querySelectorAll('.tab-btn');
  buttons.forEach((btn) => btn.addEventListener('click', () => {
    activeTab = btn.dataset.tab;
    buttons.forEach((b) => b.classList.toggle('active', b === btn));
    document.querySelectorAll('.tab-content').forEach((s) => s.classList.remove('active'));

    if (isMetricTab(activeTab)) {
      byId('tab-telemetry').classList.add('active');
      showMetric(activeTab);
    } else {
      byId(`tab-${activeTab}`).classList.add('active');
    }
  }));
}

// ============================================================
// BOTÕES PLAY / PAUSE / STOP  (POST /api/control/<ação>)
// ============================================================
function initRobotControls() {
  document.querySelectorAll('.ctrl-btn').forEach((btn) => btn.addEventListener('click', async () => {
    const action = btn.dataset.command;
    btn.disabled = true;  // evita clique duplo
    try {
      const res = await fetch(`/api/control/${action}`, { method: 'POST' });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.status !== 'ok') throw new Error(data.message || `HTTP ${res.status}`);
    } catch (err) {
      console.error(`[Controle] Erro em '${action}':`, err);
      alert(`Erro no comando ${action.toUpperCase()}: ${err.message}`);
    } finally {
      btn.disabled = false;
    }
  }));
}

// ============================================================
// SOCKET.IO
// ============================================================
function connectSocket() {
  if (!window.io) return console.error('Biblioteca Socket.IO não foi carregada.');
  const socket = window.io();
  socket.on('connection_status', (state) => setConnection(state.connected, state.error));
  socket.on('telemetry', onTelemetry);
  socket.on('disconnect', () => setConnection(false, 'Servidor local desconectado'));
}

// ============================================================
initJointCards();
initMainChart();
initLogs();
initTabs();
initRobotControls();
connectSocket();
