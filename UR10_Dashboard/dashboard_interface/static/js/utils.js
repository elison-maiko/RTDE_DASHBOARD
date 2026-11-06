/** Funções auxiliares: DOM e formatação. */

export const byId = (id) => document.getElementById(id);

/**
 * Cria um elemento. Usa textContent (nunca innerHTML), então textos vindos
 * do robô não injetam HTML.
 *   el('span', { className: 'badge', text: 'RUNNING' }, [filhos...])
 */
export function el(tag, { className, text, attrs, style } = {}, children = []) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  if (attrs) Object.entries(attrs).forEach(([k, v]) => node.setAttribute(k, v));
  if (style) Object.assign(node.style, style);
  node.append(...children);
  return node;
}

/** Adiciona ao fim do array e descarta os mais antigos acima de maxLen. */
export function pushCapped(arr, value, maxLen) {
  arr.push(value);
  while (arr.length > maxLen) arr.shift();
}

const pad = (n, len = 2) => String(n).padStart(len, '0');

/** Unix (segundos) -> "HH:MM:SS.mmm" */
export function formatTime(unixSeconds) {
  const d = new Date(unixSeconds * 1000);
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}.${pad(d.getMilliseconds(), 3)}`;
}

/** "12.34 Nm", ou "—" se não houver valor */
export const formatValue = (value, digits, unit = '') =>
  value == null ? '—' : `${value.toFixed(digits)}${unit ? ` ${unit}` : ''}`;

export const radToDeg = (rad) => (rad * 180) / Math.PI;
