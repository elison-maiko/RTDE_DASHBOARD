/**
 * Página /config: tabela de limites por junta e ação por métrica.
 * Lê e salva em /api/thresholds (safety/alarms.py -> thresholds.json).
 */

import { JOINT_NAMES } from './config.js';
import { socket } from './socket.js';
import { byId, el } from './utils.js';

/** Colunas da tabela. `key` = chave em thresholds.json; `field` = campo da telemetria */
const COLUMNS = [
  { key: 'current',     field: 'current',     label: 'Corrente',    unit: 'A',  step: '0.1', abs: true },
  { key: 'torque',      field: 'torque',      label: 'Torque',      unit: 'Nm', step: '1',   abs: true },
  { key: 'temperature', field: 'temperature', label: 'Temperatura', unit: '°C', step: '1',   abs: false },
];

const form = byId('thresholds-form');
const inputs = {};      // inputs[key][junta]
const actions = {};     // actions[key] = 'alert' | 'stop'
const liveEls = {};     // liveEls[key][junta] = <span> com o valor atual
let saved = null;       // última configuração salva (para "Descartar")

// ============================================================
// MONTAGEM DA TABELA
// ============================================================
function buildTable() {
  const head = byId('metric-head');
  const actionRow = byId('action-row');
  const body = byId('threshold-body');

  COLUMNS.forEach((col) => {
    head.append(el('th', {}, [
      el('span', { className: 'metric-name', text: col.label }),
      el('span', { className: 'metric-unit', text: col.abs ? `|${col.unit}|` : col.unit }),
    ]));
    actionRow.append(el('th', {}, [buildActionToggle(col.key)]));
    inputs[col.key] = [];
    liveEls[col.key] = [];
  });

  JOINT_NAMES.forEach((name, i) => {
    const cells = COLUMNS.map((col) => {
      const input = el('input', {
        className: 'limit-input',
        attrs: { type: 'number', min: '0', step: col.step, placeholder: 'desativado', 'aria-label': `${col.label} ${name}` },
      });
      input.addEventListener('input', markDirty);
      inputs[col.key].push(input);

      const live = el('span', { className: 'live-value', text: 'atual: —' });
      liveEls[col.key].push(live);

      return el('td', {}, [
        el('div', { className: 'limit-field' }, [input, el('span', { className: 'limit-unit', text: col.unit })]),
        live,
      ]);
    });
    body.append(el('tr', {}, [el('th', { className: 'joint-name', text: name }), ...cells]));
  });
}

/** Seletor "Alerta | STOP" de uma métrica */
function buildActionToggle(key) {
  const options = [
    { value: 'alert', text: '⚠ Alerta' },
    { value: 'stop', text: '⏹ STOP' },
  ];
  const wrap = el('div', { className: 'action-toggle', attrs: { role: 'radiogroup' } });

  options.forEach(({ value, text }) => {
    const btn = el('button', { className: `toggle-opt ${value}`, text, attrs: { type: 'button', 'data-value': value } });
    btn.addEventListener('click', () => {
      setAction(key, value);
      markDirty();
    });
    wrap.append(btn);
  });
  actions[key] = { wrap, value: 'alert' };
  return wrap;
}

function setAction(key, value) {
  actions[key].value = value;
  actions[key].wrap.querySelectorAll('.toggle-opt').forEach((b) => {
    b.classList.toggle('selected', b.dataset.value === value);
  });
  // colore a coluna inteira conforme a ação
  const idx = COLUMNS.findIndex((c) => c.key === key);
  inputs[key].forEach((input) => input.closest('td').classList.toggle('col-stop', value === 'stop'));
  document.querySelectorAll(`.threshold-table thead th:nth-child(${idx + 2})`)
    .forEach((th) => th.classList.toggle('col-stop', value === 'stop'));
}

// ============================================================
// CARREGAR / SALVAR
// ============================================================
function fillForm(config) {
  COLUMNS.forEach(({ key }) => {
    setAction(key, config[key].action);
    config[key].limits.forEach((v, i) => { inputs[key][i].value = v ?? ''; });
  });
  setDirty(false);
}

function readForm() {
  return Object.fromEntries(COLUMNS.map(({ key }) => [key, {
    action: actions[key].value,
    limits: inputs[key].map((input) => (input.value === '' ? null : Number(input.value))),
  }]));
}

async function load() {
  const res = await fetch('/api/thresholds');
  saved = await res.json();
  fillForm(saved);
}

async function save(e) {
  e.preventDefault();
  const config = readForm();
  setStatus('Salvando…', '');
  try {
    const res = await fetch('/api/thresholds', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || `HTTP ${res.status}`);
    saved = config;
    setDirty(false);
    setStatus('✓ Limites salvos e ativos', 'ok');
  } catch (err) {
    setStatus(`Erro ao salvar: ${err.message}`, 'error');
  }
}

function markDirty() {
  setDirty(true);
  setStatus('Alterações não salvas', 'pending');
}

function setDirty(dirty) {
  byId('save-btn').disabled = !dirty;
  byId('reset-btn').disabled = !dirty;
}

function setStatus(text, kind) {
  const status = byId('save-status');
  status.textContent = text;
  status.className = `save-status ${kind}`;
}

// ============================================================
// VALOR ATUAL (ajuda a escolher o limite)
// ============================================================
socket.on('telemetry', (sample) => {
  COLUMNS.forEach(({ key, field, abs }) => {
    sample[field].forEach((value, i) => {
      if (value == null || !liveEls[key][i]) return;
      const shown = abs ? Math.abs(value) : value;
      const limit = Number(inputs[key][i].value);
      liveEls[key][i].textContent = `atual: ${shown.toFixed(2)}`;
      liveEls[key][i].classList.toggle('over', inputs[key][i].value !== '' && shown > limit);
    });
  });
});

// ============================================================
buildTable();
form.addEventListener('submit', save);
byId('reset-btn').addEventListener('click', () => { fillForm(saved); setStatus('', ''); });
load().catch((err) => setStatus(`Erro ao carregar: ${err.message}`, 'error'));
