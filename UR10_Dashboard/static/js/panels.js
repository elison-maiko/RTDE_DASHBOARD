/**
 * Partes da interface que mostram a amostra atual:
 *  - status da conexão (cabeçalho)
 *  - cards das juntas (aba Home)
 *  - histórico de falhas (aba Fault History)
 *  - TCP pose (rodapé)
 */

import {
  JOINT_COLORS, JOINT_NAMES, METRICS, MODE_FAULT, MODE_RUNNING,
  SPARK_LEN, TEMP_CRIT_C, TEMP_WARN_C,
} from './config.js';
import { createSparkline, history, updateSparkline } from './charts.js';
import { byId, el, formatValue } from './utils.js';

// ============================================================
// STATUS DA CONEXÃO
// ============================================================
let lastTimestamp = null;

export function setConnection(connected, error) {
  const pill = byId('conn-pill');
  pill.classList.remove('ok', 'bad', 'wait');
  pill.classList.add(connected ? 'ok' : 'bad');
  byId('conn-label').textContent = connected ? 'RTDE conectado' : 'Desconectado';

  const banner = byId('error-banner');
  if (connected) {
    banner.hidden = true;
  } else if (error) {
    banner.hidden = false;
    banner.textContent = `[ERRO] ${error} — tentando reconectar…`;
  }
}

/** Taxa de amostragem (Hz) a partir do intervalo entre amostras */
export function updateRate(timestamp) {
  if (lastTimestamp != null && timestamp > lastTimestamp) {
    byId('rate').textContent = `${(1 / (timestamp - lastTimestamp)).toFixed(1)} Hz`;
  }
  lastTimestamp = timestamp;
}

// ============================================================
// CARDS DAS JUNTAS
// ============================================================
/** Métricas exibidas em cada card (chave de METRICS + rótulo) */
const CARD_METRICS = [
  { key: 'temp', label: 'Temp' },
  { key: 'torque', label: 'Torque' },
  { key: 'current', label: 'Corrente' },
];
const SPARK_METRIC = 'torque';

const cards = [];  // referências aos elementos de cada card

export function initJointCards() {
  JOINT_NAMES.forEach((name, i) => {
    const badge = el('span', { className: 'mode-badge', text: '—' });
    const values = {};
    const metrics = CARD_METRICS.map(({ key, label }) => {
      values[key] = el('span', { className: 'm-value', text: '—' });
      return el('div', { className: 'metric' }, [el('span', { className: 'm-label', text: label }), values[key]]);
    });
    const canvas = el('canvas');

    const root = el('div', { className: 'card' }, [
      el('div', { className: 'card-head' }, [el('span', { className: 'name', text: name }), badge]),
      el('div', { className: 'metrics' }, metrics),
      el('div', { className: 'spark' }, [canvas]),
    ]);
    byId('joint-grid').append(root);

    cards.push({ root, badge, values, spark: createSparkline(canvas, JOINT_COLORS[i]) });
  });
}

export function updateJointCards(sample) {
  cards.forEach((card, i) => {
    // Modo (faixa lateral + badge)
    const { code, label } = sample.joint_modes[i];
    card.root.classList.toggle('is-running', code === MODE_RUNNING);
    card.root.classList.toggle('is-fault', code === MODE_FAULT);
    card.badge.textContent = `${code} · ${label}`;
    card.badge.classList.toggle('run', code === MODE_RUNNING);
    card.badge.classList.toggle('fault', code === MODE_FAULT);

    // Valores
    for (const { key } of CARD_METRICS) {
      const { field, digits, unit } = METRICS[key];
      card.values[key].textContent = formatValue(sample[field][i], digits, unit);
    }

    // Alerta de temperatura
    const temp = sample.temperature[i];
    card.values.temp.classList.toggle('warn', temp != null && temp > TEMP_WARN_C);
    card.values.temp.classList.toggle('bad', temp != null && temp > TEMP_CRIT_C);

    updateSparkline(card.spark, history.series[i][SPARK_METRIC].slice(-SPARK_LEN));
  });
}

// ============================================================
// HISTÓRICO DE FALHAS — cada (junta, código) aparece uma vez
// ============================================================
const recordedFaults = new Set();

export function recordFaults(sample) {
  sample.joint_modes.forEach(({ code, label }, i) => {
    const key = `${i}-${code}`;
    if (code !== MODE_FAULT || recordedFaults.has(key)) return;
    recordedFaults.add(key);

    const tbody = byId('fault-body');
    tbody.querySelector('.empty-row')?.remove();
    tbody.prepend(el('tr', {}, [
      el('td', { text: new Date().toLocaleTimeString() }),
      el('td', { text: JOINT_NAMES[i], style: { color: JOINT_COLORS[i] } }),
      el('td', {}, [el('span', { className: 'mode-badge fault', text: String(code) })]),
      el('td', { text: `Alerta de estado de erro: ${label}` }),
    ]));
  });
}

// ============================================================
// TCP POSE  (X, Y, Z em metros; RX, RY, RZ em radianos)
// ============================================================
const POSE_AXES = ['x', 'y', 'z', 'rx', 'ry', 'rz'];

export function updateTcpPose(pose) {
  if (!pose) return;
  byId('pose-panel').hidden = false;
  POSE_AXES.forEach((axis, i) => { byId(`pose-${axis}`).textContent = pose[i].toFixed(4); });
}
