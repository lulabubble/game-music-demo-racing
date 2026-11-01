// ---------- Canvas + jump square ----------
const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');
let x = canvas.width / 2 - 15, y = canvas.height - 60, vy = 0, onGround = true;
const GRAVITY = 0.6, JUMP_FORCE = -12;
function jump() { if (onGround) { vy = JUMP_FORCE; onGround = false; } }
function update() {
  vy += GRAVITY; y += vy;
  const floor = canvas.height - 60;
  if (y >= floor) { y = floor; vy = 0; onGround = true; }
}
function draw() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = '#0f3460'; ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(0, canvas.height - 45);
  ctx.lineTo(canvas.width, canvas.height - 45);
  ctx.stroke();
  ctx.fillStyle = '#e94560';
  ctx.fillRect(x, y, 30, 30);
}
(function loop() { update(); draw(); requestAnimationFrame(loop); })();

// ---------- Adaptive mixer state ----------
const STEMS = ['air', 'motion', 'acceleration', 'danger'];

const MODES = [
  { name: '1 Menu',   gains: { air: 1.0, motion: 0.0, acceleration: 0.0, danger: 0.0 } },
  { name: '2 Cruise', gains: { air: 0.8, motion: 1.0, acceleration: 0.3, danger: 0.1 } },
  { name: '3 Boost',  gains: { air: 0.6, motion: 1.0, acceleration: 1.0, danger: 0.3 } },
  { name: '4 Danger', gains: { air: 0.4, motion: 0.8, acceleration: 0.7, danger: 1.0 } },
];

const BPM = 174;
const BARS_PER_MODE = 8;
const MODE_DUR_SEC = BARS_PER_MODE * 4 * 60 / BPM;

let currentModeIndex = 0;
let autoNarrative = true;
let modeStartTime = 0;

const targetGains = { air: 1.0, motion: 0.0, acceleration: 0.0, danger: 0.0 };

// ---------- Audio state ----------
let audioCtx = null, masterGain = null;
let buffers = {}, sources = {}, gains = {};
let isPlaying = false, isReady = false, manifest = null;
let loopDurationSec = null;
const dragging = { air: false, motion: false, acceleration: false, danger: false };

const audioBtn = document.getElementById('audioBtn');
const autoBtn = document.getElementById('autoBtn');
const statusEl = document.getElementById('status');
const diagEl = document.getElementById('diag');
const jumpBtn = document.getElementById('jumpBtn');
const modeLabelEl = document.getElementById('modeLabel');

jumpBtn.addEventListener('click', jump);
document.addEventListener('keydown', (e) => {
  if (e.code === 'Space') { e.preventDefault(); jump(); }
});

// ---------- Slider wiring ----------
STEMS.forEach(name => {
  const slider = document.getElementById('s-' + name);
  const valEl = document.getElementById('v-' + name);

  slider.addEventListener('pointerdown', () => { dragging[name] = true; });
  document.addEventListener('pointerup', () => { dragging[name] = false; });

  slider.addEventListener('input', () => {
    const v = parseFloat(slider.value);
    valEl.textContent = v.toFixed(2);
    if (autoNarrative) {
      autoNarrative = false;
      updateAutoBtn();
    }
    setTargetGain(name, v, 0.05);
  });

  slider.value = targetGains[name];
  valEl.textContent = targetGains[name].toFixed(2);
});

// ---------- Mode buttons ----------
document.querySelectorAll('.modeBtn').forEach(btn => {
  btn.addEventListener('click', () => {
    applyMode(parseInt(btn.dataset.mode, 10));
  });
});

autoBtn.addEventListener('click', () => {
  autoNarrative = !autoNarrative;
  updateAutoBtn();
  if (autoNarrative) {
    modeStartTime = audioCtx ? audioCtx.currentTime : 0;
    applyMode(currentModeIndex);
  }
});

function updateAutoBtn() {
  autoBtn.textContent = autoNarrative ? 'Auto' : 'Manual';
  autoBtn.classList.toggle('on', autoNarrative);
}

// ---------- Gain targeting ----------
function setTargetGain(name, value, rampTime = 0.15) {
  targetGains[name] = value;
  if (gains[name]) {
    const t = audioCtx.currentTime;
    const g = gains[name].gain;
    g.cancelScheduledValues(t);
    g.setValueAtTime(g.value, t);
    g.setTargetAtTime(value, t, rampTime);
  }
}

function applyMode(modeIndex) {
  currentModeIndex = modeIndex;
  modeStartTime = audioCtx ? audioCtx.currentTime : 0;
  const mode = MODES[modeIndex];
  STEMS.forEach(name => setTargetGain(name, mode.gains[name], 0.15));
  modeLabelEl.textContent = mode.name;
  document.querySelectorAll('.modeBtn').forEach((b, i) => {
    b.classList.toggle('active', i === modeIndex);
  });
}

// ---------- Auto-narrative tick ----------
setInterval(() => {
  if (!isPlaying || !autoNarrative || !audioCtx) return;
  if (audioCtx.currentTime - modeStartTime >= MODE_DUR_SEC) {
    applyMode((currentModeIndex + 1) % MODES.length);
  }
}, 50);

// ---------- UI feedback loop ----------
function uiTick() {
  STEMS.forEach(name => {
    if (dragging[name]) return;
    const slider = document.getElementById('s-' + name);
    const valEl = document.getElementById('v-' + name);
    let v;
    if (isPlaying && gains[name]) {
      v = gains[name].gain.value;
    } else {
      v = targetGains[name];
    }
    if (Math.abs(parseFloat(slider.value) - v) > 0.004) {
      slider.value = v;
      valEl.textContent = v.toFixed(2);
    }
  });
  requestAnimationFrame(uiTick);
}
uiTick();

// ---------- Audio loading ----------
function makeCleanBuffer(decoded, targetLength) {
  const clean = audioCtx.createBuffer(
    decoded.numberOfChannels, targetLength, audioCtx.sampleRate
  );
  for (let ch = 0; ch < decoded.numberOfChannels; ch++) {
    const src = decoded.getChannelData(ch);
    const dst = clean.getChannelData(ch);
    dst.set(src.subarray(0, Math.min(src.length, targetLength)));
  }
  return clean;
}

async function loadAll() {
  try {
    const mres = await fetch('racing_manifest.json', { cache: 'no-cache' });
    if (!mres.ok) throw new Error('manifest HTTP ' + mres.status);
    manifest = await mres.json();

    const Ctx = window.AudioContext || window.webkitAudioContext;
    try {
      audioCtx = new Ctx({ sampleRate: manifest.sampleRate });
    } catch (e) {
      audioCtx = new Ctx();
    }

    masterGain = audioCtx.createGain();
    masterGain.gain.value = 0.7;
    masterGain.connect(audioCtx.destination);

    const expectedLen = Math.round(
      manifest.loopSamples * audioCtx.sampleRate / manifest.sampleRate
    );
    const diagLines = ['ctx=' + audioCtx.sampleRate + 'Hz expected=' + expectedLen];

    await Promise.all(STEMS.map(async (name) => {
      const res = await fetch('racing_' + name + '_loop.opus', { cache: 'no-cache' });
      if (!res.ok) throw new Error(name + ': HTTP ' + res.status);
      const ab = await res.arrayBuffer();
      const decoded = await audioCtx.decodeAudioData(ab);
      buffers[name] = makeCleanBuffer(decoded, expectedLen);
      const d = decoded.length - expectedLen;
      diagLines.push(name + ': dec=' + decoded.length + ' d=' + (d >= 0 ? '+' : '') + d);
    }));

    loopDurationSec = expectedLen / audioCtx.sampleRate;
    diagEl.innerHTML = diagLines.join('<br>');

    applyMode(0);

    statusEl.textContent =
      'Ready: ' + manifest.bpm + ' BPM, ' + loopDurationSec.toFixed(6) + ' s, mode ' + MODES[0].name;
    isReady = true;
    audioBtn.disabled = false;
    audioBtn.textContent = 'Start';
  } catch (err) {
    console.error(err);
    statusEl.textContent = 'Audio load error: ' + err.message;
    audioBtn.textContent = 'Error';
  }
}

async function startPlayback() {
  if (!isReady || isPlaying) return;
  if (audioCtx.state === 'suspended') await audioCtx.resume();

  const startAt = audioCtx.currentTime + 0.08;

  STEMS.forEach(name => {
    const src = audioCtx.createBufferSource();
    src.buffer = buffers[name];
    src.loop = true;
    src.loopStart = 0;
    src.loopEnd = loopDurationSec;
    const g = audioCtx.createGain();
    g.gain.value = targetGains[name];
    src.connect(g).connect(masterGain);
    src.start(startAt);
    sources[name] = src;
    gains[name] = g;
  });

  isPlaying = true;
  modeStartTime = audioCtx.currentTime;
  audioBtn.textContent = 'Stop';
  audioBtn.classList.add('playing');
  statusEl.textContent = 'Playing — mode ' + MODES[currentModeIndex].name
    + (autoNarrative ? ' (auto)' : ' (manual)');
}

function stopPlayback() {
  if (!isPlaying) return;
  STEMS.forEach(name => {
    try { sources[name].stop(); } catch (e) {}
    try { sources[name].disconnect(); } catch (e) {}
    try { gains[name].disconnect(); } catch (e) {}
  });
  sources = {}; gains = {};
  isPlaying = false;
  audioBtn.textContent = 'Start';
  audioBtn.classList.remove('playing');
  statusEl.textContent = 'Stopped';
}

audioBtn.addEventListener('click', async () => {
  try {
    if (isPlaying) stopPlayback();
    else await startPlayback();
  } catch (err) {
    console.error(err);
    statusEl.textContent = 'Audio error: ' + err.message;
  }
});

loadAll();
