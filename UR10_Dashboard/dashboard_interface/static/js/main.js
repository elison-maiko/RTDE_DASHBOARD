/**
 * Página /monitor: abas, botões do robô e eventos em tempo real.
 *
 * Fluxo: servidor emite "telemetry" -> onTelemetry() -> logs, histórico, cards, gráfico.
 *        servidor emite "fault_event" -> Fault History (o popup fica em alerts.js).
 *
 * Arquivos:
 *   config.js  constantes (nomes, cores, métricas)
 *   utils.js   helpers de DOM e formatação
 *   socket.js  conexão Socket.IO compartilhada
 *   charts.js  histórico + gráficos (Chart.js)
 *   panels.js  status, cards, falhas, TCP pose
 *   logs.js    gravação CSV
 *   alerts.js  popup de limite excedido (todas as páginas)
 */

import { METRICS } from './config.js';
import {
  history, initMainChart, initPowerChart, isPaused, refreshMainChart, refreshPowerChart, showMetric,
} from './charts.js';
import { initLogs, recordSample } from './logs.js';
import {
  addFaultEvent, initJointCards, setConnection, setFaultHistory,
  updateJointCards, updateRate, updateTcpPose,
} from './panels.js';
import { socket } from './socket.js';
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
  updateTcpPose(sample.tcp_pose);
  if (activeTab === 'home') refreshPowerChart(sample);
  if (isMetricTab(activeTab)) refreshMainChart();
}

// ============================================================
// ABAS  (/monitor#fault abre direto a aba Fault History)
// ============================================================
function openTab(tab) {
  const btn = document.querySelector(`.tab-btn[data-tab="${tab}"]`);
  if (!btn) return;
  activeTab = tab;
  document.querySelectorAll('.tab-btn[data-tab]').forEach((b) => b.classList.toggle('active', b === btn));
  document.querySelectorAll('.tab-content').forEach((s) => s.classList.remove('active'));

  if (isMetricTab(tab)) {
    byId('tab-telemetry').classList.add('active');
    showMetric(tab);
  } else {
    byId(`tab-${tab}`).classList.add('active');
  }
  byId('power-section').hidden = tab !== 'home';  // energia do robô só na Home
}

function initTabs() {
  document.querySelectorAll('.tab-btn[data-tab]').forEach((btn) => {
    btn.addEventListener('click', () => openTab(btn.dataset.tab));
  });
  const fromHash = () => openTab(location.hash.slice(1));
  window.addEventListener('hashchange', fromHash);
  fromHash();
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
initJointCards();
initPowerChart();
initMainChart();
initLogs();
initTabs();
initRobotControls();

socket.on('connection_status', (state) => setConnection(state.connected, state.error));
socket.on('telemetry', onTelemetry);
socket.on('fault_history', setFaultHistory);
socket.on('fault_event', addFaultEvent);
socket.on('telemetry_history', (samples) => {  // histórico guardado no servidor
  history.load(samples);
  if (isMetricTab(activeTab)) refreshMainChart();
  if (activeTab === 'home' && samples.length) refreshPowerChart(samples[samples.length - 1]);
});
// Botão "Ver Fault History" do popup (alerts.js) quando já estamos nesta página
window.addEventListener('open-tab', (e) => openTab(e.detail));
socket.on('disconnect', () => setConnection(false, 'Servidor local desconectado'));
