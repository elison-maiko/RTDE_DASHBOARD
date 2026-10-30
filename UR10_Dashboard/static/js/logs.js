/**
 * Gravação de logs CSV (botão START LOGS / STOP) e aba Logs.
 * Grava todas as amostras, inclusive com o gráfico pausado.
 * Os arquivos ficam na memória do navegador até recarregar a página.
 */

import { JOINT_NAMES } from './config.js';
import { byId, el, formatTime } from './utils.js';

const TCP_COLUMNS = ['tcp_x', 'tcp_y', 'tcp_z', 'tcp_rx', 'tcp_ry', 'tcp_rz'];
const POWER_COLUMNS = [
  ['main_voltage', 'tensao_principal_V'], ['robot_voltage', 'tensao_robo_V'],
  ['robot_current', 'corrente_robo_A'], ['robot_power', 'potencia_W'], ['avg_power', 'potencia_media_W'],
];
const num = (v, digits) => (v == null ? '' : v.toFixed(digits));

let recording = false;
let lines = [];
let startedAt = null;
const savedLogs = [];

export function initLogs() {
  byId('log-btn').addEventListener('click', toggleRecording);
}

/** Adiciona a amostra ao CSV, se estiver gravando */
export function recordSample(sample, positionsDeg) {
  if (!recording) return;

  const row = [formatTime(sample.timestamp)];
  sample.joint_modes.forEach((mode, i) => {
    row.push(
      `${mode.code}:${mode.label}`,
      num(sample.temperature[i], 1),
      num(sample.torque[i], 3),
      num(sample.current[i], 3),
      num(positionsDeg?.[i], 2),
    );
  });
  row.push(...(sample.tcp_pose ? sample.tcp_pose.map((v) => v.toFixed(4)) : TCP_COLUMNS.map(() => '')));
  row.push(...POWER_COLUMNS.map(([field]) => num(sample[field], 3)));
  lines.push(row.join(','));
}

function csvHeader() {
  const cols = ['timestamp'];
  JOINT_NAMES.forEach((n) => cols.push(`${n}_modo`, `${n}_temp_C`, `${n}_torque_Nm`, `${n}_corrente_A`, `${n}_pos_deg`));
  return [...cols, ...TCP_COLUMNS, ...POWER_COLUMNS.map(([, name]) => name)].join(',');
}

function toggleRecording() {
  recording = !recording;
  byId('log-btn').classList.toggle('active', recording);
  byId('log-label').textContent = recording ? 'STOP' : 'START LOGS';

  if (recording) {
    lines = [csvHeader()];
    startedAt = new Date();
  } else {
    saveLog();
  }
}

function saveLog() {
  const samples = lines.length - 1;
  if (samples <= 0) return;

  const endedAt = new Date();
  const filename = `ur10_log_${startedAt.toISOString().replace(/[:.]/g, '-')}.csv`;
  savedLogs.unshift({
    filename,
    url: URL.createObjectURL(new Blob([lines.join('\n')], { type: 'text/csv' })),
    start: startedAt.toLocaleTimeString(),
    end: endedAt.toLocaleTimeString(),
    duration: `${((endedAt - startedAt) / 1000).toFixed(1)}s`,
    samples,
  });

  byId('logs-body').replaceChildren(...savedLogs.map((log) => el('tr', {}, [
    el('td', { text: log.filename }),
    el('td', { text: log.start }),
    el('td', { text: log.end }),
    el('td', { text: log.duration }),
    el('td', { text: String(log.samples) }),
    el('td', {}, [el('a', { className: 'download-link', text: '⬇ Baixar', attrs: { href: log.url, download: log.filename } })]),
  ])));
}
