/**
 * Gráficos (Chart.js):
 *  - history         : buffer com o histórico de telemetria
 *  - createSparkline : mini-gráfico dos cards da Home
 *  - gráfico grande  : abas Torque / Current / Temperature
 *      zoom com a roda do mouse, arrastar para navegar, Shift+roda para rolar;
 *      ao interagir sai do modo "ao vivo" (botão "Voltar ao vivo" retorna).
 */

import { BUFFER_LEN, JOINT_COLORS, JOINT_NAMES, LIVE_WINDOW, METRICS, THEME } from './config.js';
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

  push(sample, positionsDeg) {
    pushCapped(this.labels, formatTime(sample.timestamp), BUFFER_LEN);
    pushCapped(this.positions, positionsDeg, BUFFER_LEN);
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
