/**
 * Gráficos (Chart.js):
 *  - history         : buffer com o histórico de telemetria
 *  - createSparkline : mini-gráfico dos cards da Home
 *  - gráfico de energia: aba Home (tensões, corrente, potência)
 *  - gráfico grande  : abas Torque / Current / Temperature
 *      zoom com a roda do mouse, arrastar para navegar, Shift+roda para rolar;
 *      ao interagir sai do modo "ao vivo" (botão "Voltar ao vivo" retorna).
 */

import {
  BUFFER_LEN, JOINT_COLORS, JOINT_NAMES, LIVE_WINDOW, METRICS, POWER_METRICS, POWER_WINDOW, THEME,
} from './config.js';
import { byId, el, formatTime, pushCapped } from './utils.js';

const { Chart } = window;

// ============================================================
// HISTÓRICO
// ============================================================
export const history = {
  labels: [],     // horários (eixo X)
  positions: [],  // posição das juntas em graus, por amostra
  // series[junta][métrica] = [valores...]
  series: JOINT_NAMES.map(() => Object.fromEntries(Object.keys(METRICS).map((k) => [k, []]))),
  // power[campo] = [valores...]  (tensão, corrente e potência do robô)
  power: Object.fromEntries(POWER_METRICS.map(({ field }) => [field, []])),

  push(sample, positionsDeg) {
    pushCapped(this.labels, formatTime(sample.timestamp), BUFFER_LEN);
    pushCapped(this.positions, positionsDeg, BUFFER_LEN);
    for (const { field } of POWER_METRICS) pushCapped(this.power[field], sample[field] ?? null, BUFFER_LEN);
    this.series.forEach((joint, i) => {
      for (const [key, meta] of Object.entries(METRICS)) {
        pushCapped(joint[key], sample[meta.field][i] ?? 0, BUFFER_LEN);
      }
    });
  },
};

// ============================================================
// MINI-GRÁFICO (cards)
// ============================================================
export function createSparkline(canvas, color) {
  if (!Chart) return null;
  return new Chart(canvas, {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        data: [], borderColor: color, borderWidth: 1.5, pointRadius: 0, tension: 0.3,
        fill: true, backgroundColor: `${color}14`, // ~8% de opacidade
      }],
    },
    options: {
      animation: false,
      responsive: true,
      maintainAspectRatio: false,
      scales: { x: { display: false }, y: { display: false } },
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
    },
  });
}

export function updateSparkline(chart, data) {
  if (!chart) return;
  chart.data.datasets[0].data = data;
  chart.data.labels = data.map(() => '');
  chart.update('none');
}

// ============================================================
// GRÁFICO DE ENERGIA (aba Home) — tensões, corrente e potência no mesmo
// gráfico, cada unidade com seu eixo Y (V à esquerda, A e W à direita).
// Botões ao lado ligam/desligam cada parâmetro e mostram o valor atual.
// ============================================================
const POWER_AXES = {
  V: { position: 'left', grid: true },
  A: { position: 'right', grid: false },
  W: { position: 'right', grid: false },
};
let powerChart = null;
const powerValues = {};  // campo -> <span> com o valor atual no botão

export function initPowerChart() {
  POWER_METRICS.forEach((m, i) => {
    const icon = el('span', { className: 'icon', text: '●', style: { color: m.color } });
    powerValues[m.field] = el('span', { className: 'power-btn-value', text: '—' });
    const btn = el('button', { className: 'joint-btn active', attrs: { type: 'button' } },
      [icon, el('span', { text: m.label }), powerValues[m.field]]);

    btn.addEventListener('click', () => {
      const visible = !btn.classList.contains('active');
      btn.classList.toggle('active', visible);
      icon.textContent = visible ? '●' : '○';
      powerChart?.setDatasetVisibility(i, visible);
      powerChart?.update('none');
    });
    byId('power-buttons').append(btn);
  });

  if (!Chart) return;
  powerChart = new Chart(byId('power-chart'), powerChartOptions());
}

/** Atualiza os valores dos botões e o gráfico com o histórico */
export function refreshPowerChart(sample) {
  for (const m of POWER_METRICS) {
    const v = sample[m.field];
    powerValues[m.field].textContent = v == null ? '—' : `${v.toFixed(m.digits)} ${m.unit}`;
  }
  if (!powerChart) return;
  const from = Math.max(0, history.labels.length - POWER_WINDOW);
  powerChart.data.labels = history.labels.slice(from);
  powerChart.data.datasets.forEach((ds, i) => { ds.data = history.power[POWER_METRICS[i].field].slice(from); });
  powerChart.update('none');
}

function powerChartOptions() {
  const ticks = { color: THEME.textDim, font: { family: THEME.font, size: 11 } };
  const scales = {
    x: {
      grid: { color: THEME.line },
      ticks: {
        ...ticks, maxRotation: 0, autoSkip: true, maxTicksLimit: 10,
        callback(value) { return String(this.getLabelForValue(value)).split('.')[0]; },
      },
    },
  };
  for (const [unit, { position, grid }] of Object.entries(POWER_AXES)) {
    scales[unit] = {
      position,
      display: 'auto',  // some o eixo se todos os parâmetros dele estiverem desligados
      grace: '10%',
      grid: { color: THEME.line, drawOnChartArea: grid },
      ticks,
      title: { display: true, text: unit, color: THEME.textDim, font: { family: THEME.font, weight: '700' } },
    };
  }

  return {
    type: 'line',
    data: {
      labels: [],
      datasets: POWER_METRICS.map((m) => ({
        label: m.label,
        data: [],
        yAxisID: m.unit,
        borderColor: m.color,
        backgroundColor: m.color,
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        pointHoverBorderColor: THEME.bg,
        tension: 0.2,
      })),
    },
    options: {
      animation: false,
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      scales,
      plugins: {
        legend: { labels: { color: THEME.text, font: { family: THEME.font } }, onClick: null },
        tooltip: {
          backgroundColor: THEME.panel,
          borderColor: THEME.line,
          borderWidth: 1,
          titleColor: THEME.accent,
          titleFont: { family: THEME.font, weight: '700' },
          bodyColor: THEME.text,
          bodyFont: { family: THEME.font },
          padding: 10,
          usePointStyle: true,
          boxPadding: 4,
          callbacks: {
            label: (item) => {
              const m = POWER_METRICS[item.datasetIndex];
              const v = item.parsed.y;
              return ` ${m.label}: ${v != null ? v.toFixed(m.digits) : '—'} ${m.unit}`;
            },
          },
        },
      },
    },
  };
}

// ============================================================
// GRÁFICO GRANDE
// ============================================================
const jointVisible = JOINT_NAMES.map(() => true);
let mainChart = null;
let metricKey = 'torque';
let paused = false;
let liveFollow = true;

export const isPaused = () => paused;

export function initMainChart() {
  buildJointButtons();

  byId('pause-btn').addEventListener('click', togglePause);
  byId('live-btn').addEventListener('click', backToLive);
  byId('main-chart').addEventListener('wheel', (e) => {  // Shift + roda = rolar no tempo
    if (!mainChart || !e.shiftKey) return;
    e.preventDefault();
    leaveLiveFollow();
    mainChart.pan({ x: -e.deltaY }, undefined, 'default');
  }, { passive: false });

  if (!Chart) return console.warn('Chart.js não carregou — gráficos desativados.');
  if (window.ChartZoom) Chart.register(window.ChartZoom);
  mainChart = new Chart(byId('main-chart'), mainChartOptions());
}

/** Troca a métrica exibida (chave de METRICS) */
export function showMetric(key) {
  metricKey = key;
  byId('chart-title').textContent = METRICS[key].title;
  refreshMainChart();
}

/** Redesenha com os dados atuais do histórico */
export function refreshMainChart() {
  if (!mainChart) return;
  const { labels } = history;

  mainChart.data.labels = labels;
  mainChart.data.datasets.forEach((ds, i) => { ds.data = history.series[i][metricKey]; });

  if (liveFollow && labels.length) {
    mainChart.options.scales.x.min = labels[Math.max(0, labels.length - LIVE_WINDOW)];
    mainChart.options.scales.x.max = labels[labels.length - 1];
  }
  mainChart.update('none');
}

function buildJointButtons() {
  JOINT_NAMES.forEach((name, i) => {
    const icon = el('span', { className: 'icon', text: '●', style: { color: JOINT_COLORS[i] } });
    const btn = el('button', { className: 'joint-btn active', attrs: { type: 'button' } }, [icon, el('span', { text: name })]);

    btn.addEventListener('click', () => {
      jointVisible[i] = !jointVisible[i];
      btn.classList.toggle('active', jointVisible[i]);
      icon.textContent = jointVisible[i] ? '●' : '○';
      mainChart?.setDatasetVisibility(i, jointVisible[i]);
      mainChart?.update('none');
    });

    byId('joint-buttons').append(btn);
  });
}

function togglePause() {
  paused = !paused;
  byId('pause-btn').classList.toggle('is-paused', paused);
  byId('pause-icon').textContent = paused ? '▶' : '⏸';
  byId('pause-label').textContent = paused ? 'Retomar' : 'Pausar';
}

function leaveLiveFollow() {
  liveFollow = false;
  byId('live-btn').hidden = false;
}

function backToLive() {
  liveFollow = true;
  byId('live-btn').hidden = true;
  mainChart?.resetZoom?.('none');
  refreshMainChart();
}

function mainChartOptions() {
  return {
    type: 'line',
    data: {
      labels: [],
      datasets: JOINT_NAMES.map((name, i) => ({
        label: name,
        data: [],
        borderColor: JOINT_COLORS[i],
        backgroundColor: JOINT_COLORS[i],
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        pointHoverBorderColor: THEME.bg,
        tension: 0.2,
        hidden: !jointVisible[i],
      })),
    },
    options: {
      animation: false,
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: {
          grid: { color: THEME.line },
          ticks: {
            color: THEME.textDim,
            maxRotation: 0,
            autoSkip: true,
            callback(value) {  // "HH:MM:SS" no eixo, sem milissegundos
              const label = this.getLabelForValue(value);
              return typeof label === 'string' ? label.split('.')[0] : label;
            },
          },
        },
        y: { grid: { color: THEME.line }, ticks: { color: THEME.textDim } },
      },
      plugins: {
        legend: { labels: { color: THEME.text, font: { family: THEME.font } } },
        zoom: {
          limits: { x: { min: 'original', max: 'original' } },
          pan: { enabled: true, mode: 'x', onPanStart: () => { leaveLiveFollow(); return true; } },
          zoom: {
            wheel: { enabled: true },
            pinch: { enabled: true },
            mode: 'x',
            onZoomStart: () => { leaveLiveFollow(); return true; },
          },
        },
        tooltip: {
          backgroundColor: THEME.panel,
          borderColor: THEME.line,
          borderWidth: 1,
          titleColor: THEME.accent,
          titleFont: { family: THEME.font, weight: '700' },
          bodyColor: THEME.text,
          bodyFont: { family: THEME.font },
          padding: 10,
          usePointStyle: true,
          boxPadding: 4,
          callbacks: {
            label: (item) => {
              const { unit, digits } = METRICS[metricKey];
              const value = item.parsed.y;
              const pos = history.positions[item.dataIndex]?.[item.datasetIndex];
              const posStr = pos != null ? `  ·  pos: ${pos.toFixed(1)}°` : '';
              return ` ${item.dataset.label}: ${value != null ? value.toFixed(digits) : '—'} ${unit}${posStr}`;
            },
          },
        },
      },
    },
  };
}
