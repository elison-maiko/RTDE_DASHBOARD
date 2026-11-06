/**
 * Configuração do frontend.
 * Os valores do robô vêm do app.py (FRONTEND_CONFIG) via <script id="app-config">.
 */

const server = JSON.parse(document.getElementById('app-config').textContent);

export const JOINT_NAMES = server.jointNames;
export const MODE_RUNNING = server.modeRunning;
export const MODE_FAULT = server.modeFault;
export const TEMP_WARN_C = server.tempWarnC;
export const TEMP_CRIT_C = server.tempCritC;

/** Cor de cada junta. Hex para permitir sufixo de transparência. */
export const JOINT_COLORS = ['#ffb020', '#45d6a8', '#5b8fd9', '#ff5a5f', '#a06ee1', '#00f2fe'];

/**
 * Métricas do gráfico grande. A chave é o `data-tab` da aba no monitor.html;
 * `field` é o nome do campo no evento `telemetry` (rtde_data_receive/robot.py -> read()).
 */
export const METRICS = {
  torque:  { field: 'torque',      title: 'EVOLUÇÃO DE TORQUE NO TEMPO',      unit: 'Nm', digits: 2 },
  current: { field: 'current',     title: 'EVOLUÇÃO DE CORRENTE NO TEMPO',    unit: 'A',  digits: 2 },
  temp:    { field: 'temperature', title: 'EVOLUÇÃO DE TEMPERATURA NO TEMPO', unit: '°C', digits: 1 },
};

/**
 * Gráfico "Energia do robô" (aba Home, abaixo do TCP Pose).
 * `field` é o campo no evento `telemetry` (rtde_data_receive/robot.py -> read()).
 * Cada unidade (V, A, W) tem o próprio eixo Y no gráfico.
 */
export const POWER_METRICS = [
  { field: 'main_voltage',  label: 'Tensão principal', unit: 'V', digits: 1, color: '#a06ee1' },
  { field: 'robot_voltage', label: 'Tensão do robô',   unit: 'V', digits: 1, color: '#5b8fd9' },
  { field: 'robot_current', label: 'Corrente do robô', unit: 'A', digits: 2, color: '#45d6a8' },
  { field: 'avg_power',     label: 'Potência média',   unit: 'W', digits: 1, color: '#ffb020' },
];
export const POWER_WINDOW = 600;  // pontos visíveis no gráfico de energia (~60 s a 10 Hz)

export const BUFFER_LEN = 3000;  // amostras guardadas (~5 min a 10 Hz)
export const LIVE_WINDOW = 200;  // amostras visíveis no modo "ao vivo"
export const SPARK_LEN = 100;    // pontos do mini-gráfico dos cards

/** Cores do tema lidas do style.css, para o Chart.js usar as mesmas */
const css = getComputedStyle(document.documentElement);
const cssVar = (name) => css.getPropertyValue(name).trim();

export const THEME = {
  bg: cssVar('--bg'),
  panel: cssVar('--panel'),
  line: cssVar('--line'),
  text: cssVar('--text'),
  textDim: cssVar('--text-dim'),
  accent: cssVar('--accent'),
  font: 'IBM Plex Mono',
};
