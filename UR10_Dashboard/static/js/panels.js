/**
 * Partes da interface que mostram a amostra atual:
 *  - status da conexão (cabeçalho)
 *  - cards das juntas (aba Home)
 *  - histórico de falhas + popup Info (aba Fault History)
 *  - TCP pose
 */

import {
  JOINT_COLORS, JOINT_NAMES, METRICS, MODE_FAULT, MODE_RUNNING,
  POWER_METRICS, SPARK_LEN, TEMP_CRIT_C, TEMP_WARN_C,
} from './config.js';
import { createSparkline, history, updateSparkline } from './charts.js';
import { byId, el, formatValue, radToDeg } from './utils.js';

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
// HISTÓRICO DE FALHAS — eventos vêm do servidor (alarms.py)
//   kind "fault"     -> junta em modo FAULT
//   kind "threshold" -> limite excedido (action "alert" ou "stop")
// ============================================================
const ACTION_TEXT = { alert: '⚠ Alerta', stop: '⏹ STOP' };
let faultCount = 0;

export function addFaultEvent(event) {
  const tbody = byId('fault-body');
  tbody.querySelector('.empty-row')?.remove();

  const jointIndex = JOINT_NAMES.indexOf(event.joint);
  const level = event.kind === 'fault' || event.action === 'stop' ? 'fault' : 'warn';

  tbody.prepend(el('tr', { className: `fault-row ${level}` }, [
    el('td', { text: new Date(event.time * 1000).toLocaleTimeString() }),
    el('td', { text: event.joint, style: { color: JOINT_COLORS[jointIndex] } }),
    el('td', {}, [el('span', { className: `mode-badge ${level}`, text: event.code })]),
    el('td', { text: event.message }),
    el('td', {}, [el('div', { className: 'action-cell' }, [
      el('span', { className: `action-tag ${event.action || 'none'}`, text: ACTION_TEXT[event.action] || '—' }),
      infoButton(event),
    ])]),
  ]));

  faultCount += 1;
  const badge = byId('fault-count');
  badge.hidden = false;
  badge.textContent = faultCount;
}

export function setFaultHistory(events) {
  faultCount = 0;
  byId('fault-body').replaceChildren(
    el('tr', { className: 'empty-row' }, [el('td', { text: 'Nenhum registro de falha detectado.', attrs: { colspan: '5' } })]),
  );
  byId('fault-count').hidden = true;
  events.forEach(addFaultEvent);
}

// ============================================================
// POPUP INFO — "foto" do robô no momento do evento (event.snapshot,
// montado em alarms.py com os campos de SNAPSHOT_FIELDS)
// ============================================================
const infoModal = byId('info-modal');
byId('info-close').addEventListener('click', () => infoModal.close());
byId('info-ok').addEventListener('click', () => infoModal.close());
infoModal.addEventListener('click', (e) => { if (e.target === infoModal) infoModal.close(); }); // clique fora fecha

function infoButton(event) {
  const btn = el('button', { className: 'info-btn', text: 'Info', attrs: { type: 'button' } });
  if (event.snapshot) btn.addEventListener('click', () => openFaultInfo(event));
  else Object.assign(btn, { disabled: true, title: 'Evento sem dados registrados' });
  return btn;
}

/** Colunas da tabela de juntas do popup: campo da snapshot -> formatação */
const INFO_COLUMNS = [
  { field: 'joint_positions', format: (v) => formatValue(v == null ? null : radToDeg(v), 2, '°') },
  { field: 'torque',          format: (v) => formatValue(v, 2, 'Nm') },
  { field: 'current',         format: (v) => formatValue(v, 3, 'A') },
  { field: 'temperature',     format: (v) => formatValue(v, 1, '°C') },
  { field: 'joint_voltage',   format: (v) => formatValue(v, 1, 'V') },
];

const INFO_POWER = [
  ...POWER_METRICS.slice(0, 3),
  { field: 'robot_power', label: 'Potência instantânea', unit: 'W', digits: 1 },
  POWER_METRICS[3],
];

function openFaultInfo(event) {
  const snap = event.snapshot;
  const isStop = event.kind === 'fault' || event.action === 'stop';
  infoModal.classList.toggle('level-stop', isStop);

  byId('info-kicker').textContent = event.kind === 'fault'
    ? `✖ FALHA DE JUNTA · ${event.code}`
    : `${ACTION_TEXT[event.action] || ''} · ${event.metric.toUpperCase()}`;
  byId('info-title').textContent = event.joint;
  byId('info-message').textContent = event.message;
  byId('info-time').textContent = new Date(event.time * 1000).toLocaleString();

  // Tabela das juntas: destaca a junta do evento e a métrica que passou do limite
  byId('info-joints').replaceChildren(...JOINT_NAMES.map((name, i) => {
    const isEventJoint = name === event.joint;
    return el('tr', { className: isEventJoint ? 'is-event' : '' }, [
      el('td', {}, [el('span', { className: 'info-dot', style: { background: JOINT_COLORS[i] } }), name]),
      ...INFO_COLUMNS.map(({ field, format }) => el('td', {
        text: format(snap[field]?.[i]),
        className: isEventJoint && field === event.field ? 'is-over' : '',
      })),
    ]);
  }));

  byId('info-tcp').replaceChildren(...POSE_LABELS.map((axis, i) => infoItem(axis, snap.tcp_pose ? poseText(snap.tcp_pose[i], i) : '—')));
  byId('info-power').replaceChildren(...INFO_POWER.map((m) => infoItem(m.label, formatValue(snap[m.field], m.digits, m.unit))));

  infoModal.showModal();
}

const infoItem = (label, value) => el('div', { className: 'info-item' }, [
  el('span', { className: 'reading-label', text: label }),
  el('span', { className: 'info-value', text: value }),
]);

// ============================================================
// TCP POSE em relação à base — como no PolyScope:
// X, Y, Z em mm; RX, RY, RZ (vetor de rotação) em rad
// ============================================================
const POSE_LABELS = ['X', 'Y', 'Z', 'RX', 'RY', 'RZ'];
const poseText = (v, i) => (i < 3 ? `${(v * 1000).toFixed(2)} mm` : `${v.toFixed(3)} rad`);

export function updateTcpPose(pose) {
  if (!pose) return;
  byId('pose-panel').hidden = false;
  POSE_LABELS.forEach((axis, i) => { byId(`pose-${axis.toLowerCase()}`).textContent = poseText(pose[i], i); });
}
