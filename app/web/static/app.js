/* ── Traffic Monitor — app.js ───────────────────────────────────────────── */

// ── Tab navigation ──────────────────────────────────────────────────────────
document.querySelectorAll('.nav-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add('active');
  });
});

// ── Helpers ─────────────────────────────────────────────────────────────────
const fmt = v => (v && v !== '') ? parseFloat(v).toFixed(1) + ' min' : '—';
const fmtN = v => (v && v !== '') ? parseFloat(v).toFixed(1) : null;

function stateLabel(s) {
  if (s === 'BELOW_THRESHOLD') return { text: '🟢 Sous le seuil', cls: 'below' };
  if (s === 'ABOVE_THRESHOLD') return { text: '🔴 Au-dessus',     cls: 'above' };
  return { text: '⚪ Inconnu', cls: 'unknown' };
}

function stateCellClass(s) {
  if (s === 'BELOW_THRESHOLD') return 'state-below';
  if (s === 'ABOVE_THRESHOLD') return 'state-above';
  return '';
}

// ── State ───────────────────────────────────────────────────────────────────
async function loadState() {
  try {
    const data = await fetch('/api/state').then(r => r.json());
    const { text: mt, cls: mc } = stateLabel(data.morning);
    const { text: et, cls: ec } = stateLabel(data.evening);
    document.getElementById('morning-state').textContent = mt;
    document.getElementById('morning-state').className = 'trip-state ' + mc;
    document.getElementById('evening-state').textContent = et;
    document.getElementById('evening-state').className = 'trip-state ' + ec;
    const ts = data.last_updated
      ? new Date(data.last_updated).toLocaleTimeString('fr-CA', { hour: '2-digit', minute: '2-digit' })
      : '—';
    document.getElementById('last-updated').textContent = ts;
  } catch (e) { console.error('state error', e); }
}

// ── Logs ─────────────────────────────────────────────────────────────────────
let allLogs = [];

async function loadLogs() {
  try {
    allLogs = await fetch('/api/logs').then(r => r.json());
    renderLogs();
    renderLatest();
    renderCharts();
  } catch (e) { console.error('logs error', e); }
}

function renderLogs() {
  const search = document.getElementById('log-search').value.toLowerCase();
  const dir    = document.getElementById('log-direction').value;
  const filtered = allLogs.filter(row => {
    const matchDir  = !dir || row.direction === dir;
    const matchText = !search || JSON.stringify(row).toLowerCase().includes(search);
    return matchDir && matchText;
  });
  const tbody = document.getElementById('log-body');
  tbody.innerHTML = filtered.map(row => `
    <tr>
      <td>${row.timestamp}</td>
      <td class="dir">${row.direction === 'MORNING' ? '☀️ Matin' : '🌙 Soir'}</td>
      <td>${fmt(row.google_min)}</td>
      <td>${fmt(row.mapbox_min)}</td>
      <td>${fmt(row.here_min)}</td>
      <td>${fmt(row.ors_min)}</td>
      <td class="avg">${fmt(row.average_min)}</td>
      <td>${row.threshold_min} min</td>
      <td class="${stateCellClass(row.state)}">${row.state === 'BELOW_THRESHOLD' ? '🟢' : '🔴'} ${row.state}</td>
    </tr>
  `).join('');
  document.getElementById('log-hint').textContent =
    `${filtered.length} entrée${filtered.length !== 1 ? 's' : ''} affichée${filtered.length !== 1 ? 's' : ''}`;
}

function renderLatest() {
  const rows = allLogs.slice(0, 5);
  // On mobile show fewer columns — controlled by CSS .hide-mobile
  document.getElementById('latest-body').innerHTML = rows.map(row => `
    <tr>
      <td>${row.timestamp.slice(11, 16)}</td>
      <td class="dir">${row.direction === 'MORNING' ? '☀️' : '🌙'}</td>
      <td class="avg">${fmt(row.average_min)}</td>
      <td class="${stateCellClass(row.state)}">${row.state === 'BELOW_THRESHOLD' ? '🟢' : '🔴'}</td>
    </tr>
  `).join('');
}

// ── Charts — one per direction ────────────────────────────────────────────────
function renderCharts() {
  const recent = allLogs.slice(0, 40).reverse();
  const morning = recent.filter(r => r.direction === 'MORNING');
  const evening = recent.filter(r => r.direction === 'EVENING');

  drawTrendChart('chart-morning', morning, 'rgb(79,195,247)', 'MORNING');
  drawTrendChart('chart-evening', evening, 'rgb(124,77,255)', 'EVENING');
}

function drawTrendChart(canvasId, rows, color, direction) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  const dpr  = window.devicePixelRatio || 1;
  const rect = canvas.parentElement.getBoundingClientRect();
  canvas.width  = rect.width  * dpr;
  canvas.height = rect.height * dpr;
  ctx.scale(dpr, dpr);
  const W = rect.width, H = rect.height;
  ctx.clearRect(0, 0, W, H);

  const vals = rows.map(r => fmtN(r.average_min)).filter(v => v !== null);
  const threshold = rows.length ? parseFloat(rows[rows.length - 1].threshold_min) : null;

  // Update stat pills
  updateStats(direction, vals, threshold);

  if (vals.length < 2) {
    ctx.fillStyle = 'rgba(255,255,255,.2)';
    ctx.font = '12px DM Sans, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('Pas assez de données', W / 2, H / 2);
    return;
  }

  const pad = { top: 16, right: 16, bottom: 16, left: 16 };
  const gW = W - pad.left - pad.right;
  const gH = H - pad.top  - pad.bottom;

  const allY  = threshold ? [...vals, threshold] : vals;
  const minV  = Math.max(0, Math.min(...allY) - 5);
  const maxV  = Math.max(...allY) + 10;

  const toX = i => pad.left + (i / (vals.length - 1)) * gW;
  const toY = v => pad.top  + gH - ((v - minV) / (maxV - minV)) * gH;

  // Threshold zone
  if (threshold) {
    const ty = toY(threshold);
    ctx.fillStyle = 'rgba(255,82,82,.08)';
    ctx.fillRect(pad.left, pad.top, gW, Math.max(0, ty - pad.top));

    ctx.beginPath();
    ctx.strokeStyle = 'rgba(255,82,82,.35)';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.moveTo(pad.left, ty);
    ctx.lineTo(pad.left + gW, ty);
    ctx.stroke();
    ctx.setLineDash([]);

    // Threshold label
    ctx.fillStyle = 'rgba(255,82,82,.6)';
    ctx.font = '10px DM Mono, monospace';
    ctx.textAlign = 'right';
    ctx.fillText(`${threshold}min`, pad.left + gW - 2, ty - 3);
  }

  // Gradient fill under line
  const grad = ctx.createLinearGradient(0, pad.top, 0, H);
  grad.addColorStop(0, color.replace('rgb', 'rgba').replace(')', ', .25)'));
  grad.addColorStop(1, color.replace('rgb', 'rgba').replace(')', ', 0)'));

  ctx.beginPath();
  vals.forEach((v, i) => {
    i === 0 ? ctx.moveTo(toX(i), toY(v)) : ctx.lineTo(toX(i), toY(v));
  });
  ctx.lineTo(toX(vals.length - 1), H);
  ctx.lineTo(toX(0), H);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();

  // Line
  ctx.beginPath();
  ctx.strokeStyle = color;
  ctx.lineWidth = 2.5;
  ctx.lineJoin = 'round';
  ctx.lineCap = 'round';
  vals.forEach((v, i) => {
    i === 0 ? ctx.moveTo(toX(i), toY(v)) : ctx.lineTo(toX(i), toY(v));
  });
  ctx.stroke();

  // Historical dots (small)
  vals.slice(0, -1).forEach((v, i) => {
    ctx.beginPath();
    ctx.arc(toX(i), toY(v), 2.5, 0, Math.PI * 2);
    ctx.fillStyle = color.replace('rgb', 'rgba').replace(')', ', .5)');
    ctx.fill();
  });

  // Current value dot (big, colored by threshold)
  const last  = vals[vals.length - 1];
  const lastX = toX(vals.length - 1);
  const lastY = toY(last);
  const aboveThreshold = threshold && last > threshold;
  const dotColor = aboveThreshold ? '#ff5252' : '#69f0ae';

  ctx.beginPath();
  ctx.arc(lastX, lastY, 5, 0, Math.PI * 2);
  ctx.fillStyle = dotColor;
  ctx.fill();

  // Glow ring
  ctx.beginPath();
  ctx.arc(lastX, lastY, 8, 0, Math.PI * 2);
  ctx.strokeStyle = dotColor.replace('#', 'rgba(').replace(/(..)(..)(..)/, (_, r, g, b) =>
    `${parseInt(r,16)}, ${parseInt(g,16)}, ${parseInt(b,16)}`).replace('rgba(', 'rgba(') + ', .3)';
  // Simpler glow:
  ctx.strokeStyle = aboveThreshold ? 'rgba(255,82,82,.3)' : 'rgba(105,240,174,.3)';
  ctx.lineWidth = 2;
  ctx.stroke();

  // Current value label
  ctx.fillStyle = dotColor;
  ctx.font = 'bold 11px DM Mono, monospace';
  ctx.textAlign = lastX > W - 50 ? 'right' : 'left';
  ctx.fillText(`${last.toFixed(0)}min`, lastX + (lastX > W - 50 ? -10 : 10), lastY - 8);
}

function updateStats(direction, vals, threshold) {
  const prefix = direction === 'MORNING' ? 'morning' : 'evening';
  if (!vals.length) return;

  const current = vals[vals.length - 1];
  const min     = Math.min(...vals);
  const max     = Math.max(...vals);

  // Trend: compare last 3 vs previous 3
  let trendIcon = '→';
  if (vals.length >= 6) {
    const recent = vals.slice(-3).reduce((a, b) => a + b, 0) / 3;
    const prev   = vals.slice(-6, -3).reduce((a, b) => a + b, 0) / 3;
    const diff   = recent - prev;
    if (diff > 2)       trendIcon = '↑';
    else if (diff < -2) trendIcon = '↓';
  }

  const el = id => document.getElementById(`${prefix}-${id}`);
  if (el('current'))   el('current').textContent   = `${current.toFixed(0)} min`;
  if (el('min'))       el('min').textContent        = `${min.toFixed(0)} min`;
  if (el('max'))       el('max').textContent        = `${max.toFixed(0)} min`;
  if (el('threshold')) el('threshold').textContent  = threshold ? `${threshold} min` : '—';
  if (el('trend')) {
    el('trend').textContent = trendIcon;
    el('trend').className   = 'trend-icon ' + (trendIcon === '↑' ? 'up' : trendIcon === '↓' ? 'down' : 'flat');
  }
}

// ── Settings ─────────────────────────────────────────────────────────────────
async function loadSettings() {
  try {
    const data = await fetch('/api/settings').then(r => r.json());
    const form = document.getElementById('settings-form');
    Object.entries(data).forEach(([k, v]) => {
      const el = form.querySelector(`[name="${k}"]`);
      if (el) el.value = v;
    });
  } catch (e) { console.error('settings error', e); }
}

document.getElementById('settings-form').addEventListener('submit', async e => {
  e.preventDefault();
  const status   = document.getElementById('save-status');
  const formData = new FormData(e.target);
  const data     = Object.fromEntries(formData.entries());
  try {
    const res = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(await res.text());
    status.textContent = '✓ Sauvegardé';
    status.className = 'ok';
  } catch (err) {
    status.textContent = '✗ Erreur: ' + err.message;
    status.className = 'err';
  }
  setTimeout(() => { status.textContent = ''; status.className = ''; }, 3000);
});

// ── Log filters ───────────────────────────────────────────────────────────────
document.getElementById('log-search').addEventListener('input', renderLogs);
document.getElementById('log-direction').addEventListener('change', renderLogs);

// ── Refresh ───────────────────────────────────────────────────────────────────
document.getElementById('btn-refresh').addEventListener('click', async function () {
  this.classList.add('spinning');
  await Promise.all([loadState(), loadLogs()]);
  this.classList.remove('spinning');
});

// ── Route labels ──────────────────────────────────────────────────────────────
async function setRouteLabels() {
  try {
    const s = await fetch('/api/settings').then(r => r.json());
    const short = addr => (addr || '').split(',')[0] || '—';
    document.getElementById('morning-route').textContent =
      `${short(s.MORNING_ORIGIN)} → ${short(s.MORNING_DESTINATION)}`;
    document.getElementById('evening-route').textContent =
      `${short(s.EVENING_ORIGIN)} → ${short(s.EVENING_DESTINATION)}`;
  } catch (_) {}
}

// Redraw charts on resize
window.addEventListener('resize', () => { if (allLogs.length) renderCharts(); });

// ── Init ──────────────────────────────────────────────────────────────────────
(async () => {
  await Promise.all([loadState(), loadLogs(), loadSettings(), setRouteLabels()]);
})();

setInterval(async () => { await Promise.all([loadState(), loadLogs()]); }, 120_000);
