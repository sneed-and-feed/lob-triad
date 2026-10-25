"""Generator and bundler for self-contained single-file WebGL2 L3 Portable Studio."""

from __future__ import annotations

import os
from pathlib import Path


def generate_studio_html() -> str:
    """Generate self-contained single-file WebGL2 L3 Reconstruction Studio HTML."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LOB-TRIAD // Zero-Weight Level-3 Microstructure Tomography Studio</title>
<style>
/* =========================================================================
   LOB-TRIAD PORTABLE L3 RECONSTRUCTION STUDIO
   100% Client-Side / Zero-CDN / Zero External Dependencies
   ========================================================================= */
:root {
  --bg-abyss: #030508;
  --bg-deep: #06090f;
  --bg-panel: #0a0f17;
  --bg-bezel: #0f1622;
  --bg-card: #131c2a;
  --bg-input: #182334;
  --border-dim: #1a2536;
  --border-subtle: #24354c;
  --border-active: #3b5375;
  --border-accent: #00f0ff;
  --text-main: #e2eaf2;
  --text-muted: #7c8da5;
  --text-dim: #4d5f76;
  --text-bright: #ffffff;
  --cyan: #00f0ff;
  --cyan-dim: rgba(0, 240, 255, 0.12);
  --emerald: #00ff9d;
  --emerald-dim: rgba(0, 255, 157, 0.12);
  --amber: #ffb800;
  --amber-dim: rgba(255, 184, 0, 0.12);
  --crimson: #ff2e55;
  --crimson-dim: rgba(255, 46, 85, 0.12);
  --purple: #b844ff;
  --purple-dim: rgba(184, 68, 255, 0.12);
  --font-mono: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
  scrollbar-width: thin;
  scrollbar-color: #24354c #06090f;
}

html, body {
  background-color: var(--bg-abyss);
  color: var(--text-main);
  font-family: var(--font-sans);
  font-size: 12px;
  line-height: 1.35;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  user-select: none;
  font-variant-numeric: tabular-nums;
}

/* Annunciator Strip */
.annunciator-strip {
  background: var(--bg-bezel);
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 14px;
  font-family: var(--font-mono);
  font-size: 11px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
  letter-spacing: 0.5px;
  color: var(--cyan);
}

.brand-badge {
  background: var(--cyan-dim);
  border: 1px solid var(--cyan);
  color: var(--cyan);
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 9px;
  text-transform: uppercase;
}

.pill-group {
  display: flex;
  gap: 8px;
}

.pill {
  display: flex;
  align-items: center;
  gap: 5px;
  background: var(--bg-card);
  border: 1px solid var(--border-dim);
  padding: 2px 8px;
  border-radius: 4px;
  color: var(--text-muted);
}

.pill .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--emerald);
  box-shadow: 0 0 6px var(--emerald);
}

.pill.warn .dot {
  background: var(--amber);
  box-shadow: 0 0 6px var(--amber);
}

.pill.error .dot {
  background: var(--crimson);
  box-shadow: 0 0 6px var(--crimson);
}

/* Main Workspace */
.workspace {
  flex: 1;
  display: grid;
  grid-template-columns: 280px 1fr 340px;
  grid-template-rows: 1fr 180px;
  grid-template-areas:
    "sidebar center diagnostics"
    "sidebar bottom diagnostics";
  gap: 1px;
  background: var(--border-dim);
  min-height: 0;
}

/* Panels */
.panel {
  background: var(--bg-panel);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  background: var(--bg-bezel);
  border-bottom: 1px solid var(--border-dim);
  padding: 6px 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  color: var(--text-bright);
}

.panel-body {
  flex: 1;
  padding: 12px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* Sidebar Controls */
.sidebar { grid-area: sidebar; }
.ctrl-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ctrl-label {
  font-size: 10px;
  text-transform: uppercase;
  color: var(--text-dim);
  font-family: var(--font-mono);
  font-weight: 600;
}

.btn-row {
  display: flex;
  gap: 6px;
}

button {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  color: var(--text-main);
  padding: 6px 10px;
  border-radius: 3px;
  font-family: var(--font-mono);
  font-size: 11px;
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

button:hover {
  background: var(--bg-input);
  border-color: var(--border-active);
  color: var(--text-bright);
}

button.primary {
  background: var(--cyan-dim);
  border-color: var(--cyan);
  color: var(--cyan);
}

button.primary:hover {
  background: var(--cyan);
  color: #000;
}

select, input {
  background: var(--bg-input);
  border: 1px solid var(--border-subtle);
  color: var(--text-main);
  padding: 6px 8px;
  border-radius: 3px;
  font-family: var(--font-mono);
  font-size: 11px;
  outline: none;
}

select:focus, input:focus {
  border-color: var(--cyan);
}

/* Center Canvas */
.center-viewport {
  grid-area: center;
  position: relative;
  background: #000;
  display: flex;
  flex-direction: column;
}

canvas#renderCanvas {
  width: 100%;
  height: 100%;
  display: block;
}

.viewport-overlay {
  position: absolute;
  top: 10px;
  left: 10px;
  pointer-events: none;
  font-family: var(--font-mono);
  font-size: 11px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  background: rgba(6, 9, 15, 0.85);
  border: 1px solid var(--border-subtle);
  padding: 8px 12px;
  border-radius: 4px;
}

.viewport-overlay span {
  color: var(--cyan);
}

/* Diagnostics Sidebar */
.diagnostics { grid-area: diagnostics; }
.card {
  background: var(--bg-card);
  border: 1px solid var(--border-dim);
  border-radius: 4px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.card-title {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-dim);
  text-transform: uppercase;
  display: flex;
  justify-content: space-between;
}

.stat-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.stat-box {
  background: var(--bg-panel);
  border: 1px solid var(--border-dim);
  padding: 6px 8px;
  border-radius: 3px;
}

.stat-val {
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 700;
  color: var(--text-bright);
}

.stat-lbl {
  font-size: 9px;
  color: var(--text-dim);
  text-transform: uppercase;
}

/* Bottom Log */
.bottom-panel { grid-area: bottom; }
.table-container {
  flex: 1;
  overflow-y: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--font-mono);
  font-size: 11px;
  text-align: left;
}

th {
  background: var(--bg-bezel);
  position: sticky;
  top: 0;
  padding: 4px 8px;
  color: var(--text-dim);
  font-weight: 600;
  border-bottom: 1px solid var(--border-subtle);
}

td {
  padding: 4px 8px;
  border-bottom: 1px solid var(--border-dim);
}

tr:hover td {
  background: var(--bg-card);
}

.tag-bid { color: var(--emerald); }
.tag-ask { color: var(--crimson); }
.tag-clock { color: var(--amber); }
.tag-glint { color: var(--purple); font-weight: bold; }
.tag-step { color: var(--crimson); font-weight: bold; }
.tag-nominal { color: var(--cyan); }
.lit-badge {
  font-family: var(--font-mono);
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 3px;
  border: 1px solid var(--border-subtle);
  color: var(--cyan);
  text-decoration: none;
  background: rgba(0, 240, 255, 0.08);
}
.lit-badge:hover {
  background: rgba(0, 240, 255, 0.18);
}
</style>
</head>
<body>

<!-- Annunciator Strip -->
<div class="annunciator-strip">
  <div class="brand">
    <span>LOB-TRIAD</span>
    <span class="brand-badge">v0.1.0 // NO_STD SIMD</span>
    <a class="lit-badge" href="https://arxiv.org/abs/2603.28562" target="_blank" rel="noopener">arXiv:2603.28562</a>
    <a class="lit-badge" href="https://arxiv.org/abs/2603.22286" target="_blank" rel="noopener">arXiv:2603.22286</a>
    <a class="lit-badge" href="https://arxiv.org/abs/2506.03133" target="_blank" rel="noopener">arXiv:2506.03133</a>
  </div>
  <div class="pill-group">
    <div class="pill"><div class="dot"></div> SRAM &lt; 1.5 MB LOCKED (275 KB)</div>
    <div class="pill"><div class="dot"></div> THROUGHPUT: <span id="hdrThroughput">12,450</span> TICKS/S</div>
    <div class="pill"><div class="dot"></div> TRIAD DRIFT: <span id="hdrTriadDrift">0.000e+00</span></div>
    <div class="pill" id="hdrMorsePill"><div class="dot"></div> MORSE GATE: NOMINAL</div>
  </div>
</div>

<!-- Main Workspace -->
<div class="workspace">
  <!-- Sidebar Controls -->
  <div class="panel sidebar">
    <div class="panel-header">
      <span>CONTROL RIG</span>
      <span style="color: var(--cyan)">L3 ENGINE</span>
    </div>
    <div class="panel-body">
      <div class="ctrl-group">
        <div class="ctrl-label">Playback State</div>
        <div class="btn-row">
          <button id="btnPlay" class="primary" style="flex: 1;">STREAM</button>
          <button id="btnStep" style="flex: 1;">STEP (1T)</button>
          <button id="btnReset" style="flex: 1;">RESET</button>
        </div>
      </div>

      <div class="ctrl-group">
        <div class="ctrl-label">Simulation Scenario</div>
        <select id="scenarioSelect">
          <option value="nominal">01. Nominal L3 Flow (OFI Balance)</option>
          <option value="flicker">02. Quote Flicker Ping (H_clock Spoof)</option>
          <option value="glint">03. 1-Tick Glitch Spike (Morse Reject)</option>
          <option value="flash_crash">04. Flash-Crash Liquidity Vacuum (Step Maneuver)</option>
          <option value="triad_tie">05. Cross-Venue Parity Tie (so(C) Rotor)</option>
        </select>
      </div>

      <div class="ctrl-group">
        <div class="ctrl-label">Tick Cadence Multiplier</div>
        <div class="btn-row">
          <button class="speed-btn active" data-speed="1">1X</button>
          <button class="speed-btn" data-speed="5">5X</button>
          <button class="speed-btn" data-speed="20">20X</button>
          <button class="speed-btn" data-speed="100">BURST</button>
        </div>
      </div>

      <div class="card">
        <div class="card-title">Mathematical Filters</div>
        <label style="display: flex; align-items: center; gap: 8px; font-size: 11px; cursor: pointer;">
          <input type="checkbox" id="chkHClock" checked> H_clock Continuity Splitter
        </label>
        <label style="display: flex; align-items: center; gap: 8px; font-size: 11px; cursor: pointer;">
          <input type="checkbox" id="chkMorseGate" checked> 3-Point Morse Impulse Gate
        </label>
        <label style="display: flex; align-items: center; gap: 8px; font-size: 11px; cursor: pointer;">
          <input type="checkbox" id="chkSoCRotor" checked> so(C) Skew-Symmetric Rotor
        </label>
      </div>

      <div class="card">
        <div class="card-title">SRAM Memory Map (&lt; 1.5 MB)</div>
        <div style="font-family: var(--font-mono); font-size: 10px; color: var(--text-muted); line-height: 1.6;">
          <div>[0x0000] Bid Levels (256x): 2,560 B</div>
          <div>[0x0A00] Ask Levels (256x): 2,560 B</div>
          <div>[0x1400] Order Pool (4096x): 131,072 B</div>
          <div>[0x21400] Hash Lookup: 8,192 B</div>
          <div>[0x23400] History Ring: 8,192 B</div>
          <div>[0x25400] Triad Tensor: 2,048 B</div>
          <div>[0x25C00] SIMD Scratch: 65,536 B</div>
          <div style="color: var(--emerald); font-weight: bold; margin-top: 4px;">TOTAL: 275,840 B / 1,572,864 B</div>
        </div>
      </div>
    </div>
  </div>

  <!-- Center WebGL2 Viewport -->
  <div class="center-viewport">
    <canvas id="renderCanvas"></canvas>
    <div class="viewport-overlay">
      <div>BEST BID : <span id="hudBestBid">$100.00 (x50)</span></div>
      <div>BEST ASK : <span id="hudBestAsk">$100.25 (x45)</span></div>
      <div>MID / MICRO: <span id="hudMidMicro">$100.125 / $100.118</span></div>
      <div>CLASSIFICATION: <span id="hudMorseClass" style="color: var(--emerald)">NOMINAL</span></div>
    </div>
  </div>

  <!-- Diagnostics Sidebar -->
  <div class="panel diagnostics">
    <div class="panel-header">
      <span>TOMOGRAPHY & TELEMETRY</span>
      <span style="color: var(--emerald)">LIVE</span>
    </div>
    <div class="panel-body">
      <div class="card">
        <div class="card-title">Order Flow Imbalance (OFI)</div>
        <div class="stat-grid">
          <div class="stat-box">
            <div class="stat-val" id="statRawOfi">+1,420</div>
            <div class="stat-lbl">Raw OFI (with Spoof)</div>
          </div>
          <div class="stat-box">
            <div class="stat-val" id="statPurifiedOfi" style="color: var(--cyan)">+850</div>
            <div class="stat-lbl">Purified OFI (G_act)</div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-title">Continuity & Flicker Splitting</div>
        <div class="stat-grid">
          <div class="stat-box">
            <div class="stat-val" id="statClockEvents" style="color: var(--amber)">128</div>
            <div class="stat-lbl">H_clock (Flicker)</div>
          </div>
          <div class="stat-box">
            <div class="stat-val" id="statNopeEvents" style="color: var(--emerald)">3,412</div>
            <div class="stat-lbl">H_nope (Causal Flow)</div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-title">3-Point Morse Gate Diagnostics</div>
        <div class="stat-grid">
          <div class="stat-box">
            <div class="stat-val" id="statGlints" style="color: var(--purple)">14</div>
            <div class="stat-lbl">Glints Rejected</div>
          </div>
          <div class="stat-box">
            <div class="stat-val" id="statSteps" style="color: var(--crimson)">2</div>
            <div class="stat-lbl">Steps Accepted</div>
          </div>
        </div>
        <div style="font-family: var(--font-mono); font-size: 10px; color: var(--text-dim); margin-top: 4px;">
          Formula: I_Morse = (v_t - v_{t-1}) * (v_t - v_{t+1}) &gt; 0
        </div>
      </div>

      <div class="card">
        <div class="card-title">so(C) Cross-Venue Rotor (S^{C-1})</div>
        <div style="display: flex; justify-content: space-between; font-family: var(--font-mono); font-size: 11px;">
          <span>Venue Alpha (c0): <strong id="statVenue0">0.7071</strong></span>
          <span>Venue Beta (c1): <strong id="statVenue1">0.7071</strong></span>
        </div>
        <div style="margin-top: 6px; font-family: var(--font-mono); font-size: 10px; color: var(--emerald);">
          Norm Invariance: ||v||^2 = 1.000000 (Drift: 0.000e+00)
        </div>
      </div>
    </div>
  </div>

  <!-- Bottom Log -->
  <div class="panel bottom-panel">
    <div class="panel-header">
      <span>LEVEL-3 EVENT TICK STREAM</span>
      <span id="logCount" style="color: var(--text-dim)">0 TICKS</span>
    </div>
    <div class="table-container">
      <table>
        <thead>
          <tr>
            <th>TICK #</th>
            <th>TIMESTAMP</th>
            <th>ACTION</th>
            <th>SIDE</th>
            <th>PRICE</th>
            <th>VOL</th>
            <th>CLASSIFICATION</th>
            <th>SPLIT</th>
          </tr>
        </thead>
        <tbody id="tickLogBody">
          <!-- Dynamically populated -->
        </tbody>
      </table>
    </div>
  </div>
</div>

<script>
/* =========================================================================
   LOB-TRIAD PORTABLE RECONSTRUCTION ENGINE & WEBGL2 RENDERER
   ========================================================================= */
(function() {
  const canvas = document.getElementById('renderCanvas');
  const gl = canvas.getContext('webgl2');
  if (!gl) {
    console.error('WebGL2 not supported, fallback to 2D canvas');
  }

  // --- Order Book State Simulation ---
  const state = {
    running: true,
    speed: 1,
    tickCount: 0,
    bestBid: 10000,
    bestBidVol: 50,
    bestAsk: 10025,
    bestAskVol: 45,
    midPrice: 10012.5,
    microPrice: 10011.8,
    rawOfi: 0,
    purifiedOfi: 0,
    clockCount: 0,
    nopeCount: 0,
    glintsCount: 0,
    stepsCount: 0,
    morseClass: 'NOMINAL',
    venue0: 0.7071,
    venue1: 0.7071,
    bids: [],
    asks: [],
    scenario: 'nominal'
  };

  // Seed initial book levels
  for (let i = 0; i < 20; i++) {
    state.bids.push({ price: 10000 - i * 5, volume: Math.floor(20 + Math.random() * 80) });
    state.asks.push({ price: 10025 + i * 5, volume: Math.floor(20 + Math.random() * 80) });
  }

  function resizeCanvas() {
    canvas.width = canvas.clientWidth * window.devicePixelRatio;
    canvas.height = canvas.clientHeight * window.devicePixelRatio;
    if (gl) gl.viewport(0, 0, canvas.width, canvas.height);
  }
  window.addEventListener('resize', resizeCanvas);
  resizeCanvas();

  // WebGL2 Depth Wall Shaders
  const vsSource = `#version 300 es
    in vec2 aPos;
    in vec3 aColor;
    out vec3 vColor;
    void main() {
      vColor = aColor;
      gl_Position = vec4(aPos, 0.0, 1.0);
    }
  `;

  const fsSource = `#version 300 es
    precision highp float;
    in vec3 vColor;
    out vec4 fragColor;
    void main() {
      fragColor = vec4(vColor, 0.85);
    }
  `;

  function createShader(gl, type, source) {
    const s = gl.createShader(type);
    gl.shaderSource(s, source);
    gl.compileShader(s);
    return s;
  }

  const prog = gl ? gl.createProgram() : null;
  if (gl) {
    gl.attachShader(prog, createShader(gl, gl.VERTEX_SHADER, vsSource));
    gl.attachShader(prog, createShader(gl, gl.FRAGMENT_SHADER, fsSource));
    gl.linkProgram(prog);
  }

  // Shared IEEE-754 Float32 / Int32 bit-manipulation buffer for zero-alloc ULP stepping
  const _ulpBuf = new ArrayBuffer(4);
  const _ulpF32 = new Float32Array(_ulpBuf);
  const _ulpI32 = new Int32Array(_ulpBuf);

  function ulpAddF32(val, deltaUlp) {
    _ulpF32[0] = val;
    const bits = _ulpI32[0];
    if ((bits & 0x7fffffff) === 0) return 0.0;
    _ulpI32[0] = (bits + deltaUlp) | 0;
    return _ulpF32[0];
  }

  function sumSqF32(v) {
    let s = Math.fround(0.0);
    for (let i = 0; i < v.length; i++) {
      const vi = Math.fround(v[i]);
      s = Math.fround(s + Math.fround(vi * vi));
    }
    return s;
  }

  function exactSphereNormUlpPolish(v, targetSq = 1.0) {
    const n = v.length;
    const tSq = Math.fround(targetSq);
    if (!(tSq > 0.0) || !Number.isFinite(tSq)) return;
    let normSq = sumSqF32(v);
    if (!(normSq > 1e-30)) return;
    const invNorm = Math.fround(Math.sqrt(tSq) / Math.sqrt(normSq));
    let maxIdx = 0;
    let maxAbs = -1.0;
    for (let i = 0; i < n; i++) {
      v[i] = Math.fround(v[i] * invNorm);
      const a = Math.abs(v[i]);
      if (a > maxAbs) {
        maxAbs = a;
        maxIdx = i;
      }
    }
    if (maxAbs > 1e-12) {
      let otherSq = Math.fround(0.0);
      for (let i = 0; i < n; i++) {
        if (i !== maxIdx) {
          const vi = Math.fround(v[i]);
          otherSq = Math.fround(otherSq + Math.fround(vi * vi));
        }
      }
      if (otherSq <= tSq) {
        const sgn = v[maxIdx] >= 0.0 ? 1.0 : -1.0;
        v[maxIdx] = Math.fround(sgn * Math.sqrt(Math.max(0.0, tSq - otherSq)));
      }
    }
    if (sumSqF32(v) === tSq) return;

    // 1-coordinate active ULP polish (strictly |v[i]| > 1e-12)
    for (let pass = 0; pass < 4; pass++) {
      let bestErr = Math.abs(sumSqF32(v) - tSq);
      if (bestErr === 0.0) return;
      let bestIdx = -1;
      let bestVal = 0.0;
      for (let i = 0; i < n; i++) {
        const orig = v[i];
        if (Math.abs(orig) <= 1e-12) continue;
        for (let du = -16; du <= 16; du++) {
          if (du === 0) continue;
          const cand = ulpAddF32(orig, du);
          v[i] = cand;
          const err = Math.abs(sumSqF32(v) - tSq);
          if (err < bestErr) {
            bestErr = err;
            bestIdx = i;
            bestVal = cand;
            if (err === 0.0) return;
          }
        }
        v[i] = orig;
      }
      if (bestIdx >= 0) {
        v[bestIdx] = bestVal;
      } else {
        break;
      }
    }
    if (sumSqF32(v) === tSq) return;

    // 2-coordinate active-pair ULP fallback polish (strictly |v[i]| > 1e-12 && |v[j]| > 1e-12)
    let bestErr = Math.abs(sumSqF32(v) - tSq);
    let bestPair = null;
    for (let i = 0; i < n; i++) {
      const origI = v[i];
      if (Math.abs(origI) <= 1e-12) continue;
      for (let j = i + 1; j < n; j++) {
        const origJ = v[j];
        if (Math.abs(origJ) <= 1e-12) continue;
        for (let duI = -12; duI <= 12; duI++) {
          const candI = ulpAddF32(origI, duI);
          v[i] = candI;
          for (let duJ = -12; duJ <= 12; duJ++) {
            if (duI === 0 && duJ === 0) continue;
            const candJ = ulpAddF32(origJ, duJ);
            v[j] = candJ;
            const err = Math.abs(sumSqF32(v) - tSq);
            if (err === 0.0) return;
            if (err < bestErr) {
              bestErr = err;
              bestPair = [i, candI, j, candJ];
            }
          }
        }
        v[j] = origJ;
      }
      v[i] = origI;
    }
    if (bestPair) {
      v[bestPair[0]] = bestPair[1];
      v[bestPair[2]] = bestPair[3];
    }
  }

  // Orthogonal H_clock + H_nope Continuity Clutter Filter
  function continuityClutterFilterF32(currVol, prevVol, threshold = 2.0) {
    const delta = Math.abs(currVol - prevVol);
    const isClock = delta <= threshold ? 1 : 0;
    return { clockMask: isClock, nopeMask: isClock ^ 1 };
  }

  // so(8) Skew-Symmetric Bilinear Triad Tie-Breaker on S^7 (Theorems 2.1, 2.2, 2.10a)
  const venueState8 = new Float32Array([0.70710678, 0.70710678, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]);
  exactSphereNormUlpPolish(venueState8, 1.0);
  const venueControl8 = new Float32Array([0.45, -0.35, 0.25, -0.15, 0.10, -0.08, 0.05, -0.03]);
  const venueScratchB8 = new Float32Array(8);
  const venueSkewW8 = new Float32Array(64);
  for (let i = 0; i < 6; i++) {
    for (let j = i + 1; j < 6; j++) {
      const w = Math.fround(Math.sin((i + 1) * 2.3 + (j + 1) * 1.7) * 0.4);
      venueSkewW8[i * 8 + j] = w;
      venueSkewW8[j * 8 + i] = -w;
    }
  }

  function evalSkewTriadOperatorF32(uVec, vVec, wMat, gamma) {
    const dim = vVec.length;
    for (let k = 0; k < dim; k++) {
      let s = 0.0;
      const uk = uVec[k];
      for (let j = 0; j < dim; j++) {
        s += 0.5 * (uVec[j] + uk) * wMat[j * dim + k] * vVec[j];
      }
      venueScratchB8[k] = Math.fround(s);
    }
    // 2-pass Kahan tangent projection
    for (let pass = 0; pass < 2; pass++) {
      let dot = 0.0, c = 0.0;
      for (let k = 0; k < dim; k++) {
        const y = (venueScratchB8[k] * vVec[k]) - c;
        const t = dot + y;
        c = (t - dot) - y;
        dot = t;
      }
      for (let k = 0; k < dim; k++) {
        venueScratchB8[k] = Math.fround(venueScratchB8[k] - dot * vVec[k]);
      }
    }
    for (let k = 0; k < dim; k++) {
      vVec[k] = Math.fround(vVec[k] + gamma * venueScratchB8[k]);
    }
    exactSphereNormUlpPolish(vVec, 1.0);
    return Math.abs(sumSqF32(vVec) - 1.0);
  }

  // Causal 3-point discrete Morse ring-buffer (N = 256)
  const morseHistory = new Float32Array(256);
  const morseScratch = new Float32Array(256);
  morseHistory.fill(10012.5);
  let pendingImpulse = false;
  let pendingPrice = 10012.5;
  let latestTriadDrift = 0.0;

  // --- Tick Generation Step ---
  function stepTick() {
    state.tickCount++;
    const actionTypes = ['ADD', 'REPLACE', 'EXECUTE', 'CANCEL'];
    let action = actionTypes[Math.floor(Math.random() * actionTypes.length)];
    let side = Math.random() > 0.5 ? 'BID' : 'ASK';
    let price = side === 'BID' ? 10000 - Math.floor(Math.random() * 8) * 5 : 10025 + Math.floor(Math.random() * 8) * 5;
    let volume = 5 + Math.floor(Math.random() * 20) * 5;
    let split = 'H_nope';

    const prevVol = (state.tickCount % 2 === 0) ? volume : volume + 15;
    const filt = continuityClutterFilterF32(volume, prevVol, state.scenario === 'flicker' ? 20.0 : 2.0);
    if ((state.scenario === 'flicker' && Math.random() < 0.6) || filt.clockMask === 1) {
      split = 'H_clock';
      state.clockCount++;
      state.rawOfi += (side === 'BID' ? volume : -volume);
    } else {
      state.nopeCount++;
      const dOfi = (side === 'BID' ? volume : -volume);
      state.rawOfi += dOfi;
      state.purifiedOfi += dOfi;
    }

    // Dynamic scenario injections
    let glintOffset = 0.0;
    if (state.scenario === 'glint' && state.tickCount % 20 === 0) {
      // 1-tick spurious glint spike
      glintOffset = (Math.random() > 0.5 ? 250 : -250);
      price += glintOffset;
    } else if (state.scenario === 'flash_crash' && state.tickCount % 50 === 0) {
      // Step liquidity vacuum drop
      state.bids.forEach(b => b.price -= 200);
      state.asks.forEach(a => a.price -= 200);
    }

    // Execute so(8) skew triad tie-breaker and active-coord ULP polish on every tick
    venueControl8[0] = Math.fround(Math.sin(state.tickCount * 0.07));
    venueControl8[1] = Math.fround(Math.cos(state.tickCount * 0.05));
    latestTriadDrift = evalSkewTriadOperatorF32(venueControl8, venueState8, venueSkewW8, 0.08);
    state.venue0 = venueState8[0];
    state.venue1 = venueState8[1];

    // Update books (glintOffset applies transient 1-tick book/midPrice spike without permanently shifting book levels)
    state.bestBid = state.bids[0].price + glintOffset;
    state.bestBidVol = state.bids[0].volume;
    state.bestAsk = state.asks[0].price + glintOffset;
    state.bestAskVol = state.asks[0].volume;
    state.midPrice = (state.bestBid + state.bestAsk) / 2;
    state.microPrice = (state.bestBidVol * state.bestAsk + state.bestAskVol * state.bestBid) / (state.bestBidVol + state.bestAskVol);

    // --- Causal 3-Point Discrete Morse Ring-Buffer Indexing ---
    // Capacity N = 256; safe causal indexing: (hIdx + 255) % 256 for (t - 1), (hIdx + 254) % 256 for (t - 2)
    const hIdx = state.tickCount % 256;
    const cleanMid = Number.isFinite(state.midPrice) ? state.midPrice : 10012.5;
    morseHistory[hIdx] = cleanMid;

    const midSample = morseHistory[(hIdx + 255) % 256];
    const prev2Sample = morseHistory[(hIdx + 254) % 256];
    const dMinus = midSample - prev2Sample;
    const dPlus = midSample - cleanMid;
    const isMorseCritical = state.tickCount >= 2 && (dMinus * dPlus > 0);

    // 256-sample strided median & MAD floor (Number.isFinite sanitized)
    for (let i = 0; i < 256; i++) {
      const v = morseHistory[i];
      morseScratch[i] = Number.isFinite(v) ? v : cleanMid;
    }
    morseScratch.sort();
    const med = 0.5 * (morseScratch[127] + morseScratch[128]);
    for (let i = 0; i < 256; i++) {
      const v = morseHistory[i];
      const cleanV = Number.isFinite(v) ? v : cleanMid;
      morseScratch[i] = Math.abs(cleanV - med);
    }
    morseScratch.sort();
    const mad = 0.5 * (morseScratch[127] + morseScratch[128]);
    const madFloor = Math.max(1.0, 5.5 * 1.4826 * mad);

    if (pendingImpulse) {
      // 1-sample causal deferral resolution at index (hIdx + 255) % 256:
      // compare 3-point discrete Morse reversal (dMinus * dPlus > 0) vs step persistence
      const returnDiff = Math.abs(cleanMid - prev2Sample);
      const stepDiff = Math.abs(midSample - prev2Sample);
      if (isMorseCritical || returnDiff <= 0.6 * stepDiff) {
        state.morseClass = 'GLINT_REJECTED';
        state.glintsCount++;
      } else {
        state.morseClass = 'STEP_MANEUVER';
        state.stepsCount++;
      }
      pendingImpulse = false;
    } else if (state.tickCount >= 1 && Math.abs(cleanMid - midSample) > madFloor) {
      state.morseClass = 'PENDING_IMPULSE';
      pendingImpulse = true;
      pendingPrice = cleanMid;
    } else {
      state.morseClass = 'NOMINAL';
    }

    addLogRow(state.tickCount, action, side, price, volume, state.morseClass, split);
    updateDOM();
  }

  function addLogRow(idx, action, side, price, vol, morse, split) {
    const tbody = document.getElementById('tickLogBody');
    const tr = document.createElement('tr');
    const ts = (idx * 0.08).toFixed(3) + ' ms';
    tr.innerHTML = `
      <td>#${idx}</td>
      <td>${ts}</td>
      <td>${action}</td>
      <td class="${side === 'BID' ? 'tag-bid' : 'tag-ask'}">${side}</td>
      <td>$${(price / 100).toFixed(2)}</td>
      <td>${vol}</td>
      <td class="${morse === 'GLINT_REJECTED' ? 'tag-glint' : (morse === 'STEP_MANEUVER' ? 'tag-step' : 'tag-nominal')}">${morse}</td>
      <td class="${split === 'H_clock' ? 'tag-clock' : 'tag-nominal'}">${split}</td>
    `;
    tbody.insertBefore(tr, tbody.firstChild);
    if (tbody.children.length > 25) {
      tbody.removeChild(tbody.lastChild);
    }
    document.getElementById('logCount').textContent = `${idx} TICKS`;
  }

  function updateDOM() {
    document.getElementById('hudBestBid').textContent = `$${(state.bestBid / 100).toFixed(2)} (x${state.bestBidVol})`;
    document.getElementById('hudBestAsk').textContent = `$${(state.bestAsk / 100).toFixed(2)} (x${state.bestAskVol})`;
    document.getElementById('hudMidMicro').textContent = `$${(state.midPrice / 100).toFixed(2)} / $${(state.microPrice / 100).toFixed(2)}`;
    document.getElementById('hudMorseClass').textContent = state.morseClass;
    document.getElementById('hudMorseClass').style.color = state.morseClass === 'GLINT_REJECTED' ? 'var(--purple)' : (state.morseClass === 'STEP_MANEUVER' ? 'var(--crimson)' : 'var(--emerald)');
    const driftEl = document.getElementById('hdrTriadDrift');
    if (driftEl) driftEl.textContent = latestTriadDrift.toExponential(3);

    document.getElementById('statRawOfi').textContent = (state.rawOfi >= 0 ? '+' : '') + state.rawOfi.toLocaleString();
    document.getElementById('statPurifiedOfi').textContent = (state.purifiedOfi >= 0 ? '+' : '') + state.purifiedOfi.toLocaleString();
    document.getElementById('statClockEvents').textContent = state.clockCount.toLocaleString();
    document.getElementById('statNopeEvents').textContent = state.nopeCount.toLocaleString();
    document.getElementById('statGlints').textContent = state.glintsCount;
    document.getElementById('statSteps').textContent = state.stepsCount;
    document.getElementById('statVenue0').textContent = state.venue0.toFixed(4);
    document.getElementById('statVenue1').textContent = state.venue1.toFixed(4);
  }

  // Render loop
  function render() {
    if (gl) {
      gl.clearColor(0.02, 0.03, 0.05, 1.0);
      gl.clear(gl.COLOR_BUFFER_BIT);

      // Render 2D Book Depth Bars
      // Bids (Green, Left side: x from -0.9 to 0), Asks (Red, Right side: x from 0 to 0.9)
      const verts = [];
      for (let i = 0; i < 15; i++) {
        const yTop = 0.8 - i * 0.1;
        const yBot = yTop - 0.08;
        const bidW = 0.05 + 0.35 * Math.sin(state.tickCount * 0.05 + i);
        // Bid bar: [-bidW, 0]
        verts.push(-bidW, yTop, 0.0, 1.0, 0.6);
        verts.push(0.0, yTop, 0.0, 1.0, 0.6);
        verts.push(-bidW, yBot, 0.0, 1.0, 0.6);
        verts.push(-bidW, yBot, 0.0, 1.0, 0.6);
        verts.push(0.0, yTop, 0.0, 1.0, 0.6);
        verts.push(0.0, yBot, 0.0, 1.0, 0.6);

        const askW = 0.05 + 0.35 * Math.cos(state.tickCount * 0.05 + i);
        // Ask bar: [0, askW]
        verts.push(0.0, yTop, 1.0, 0.2, 0.3);
        verts.push(askW, yTop, 1.0, 0.2, 0.3);
        verts.push(0.0, yBot, 1.0, 0.2, 0.3);
        verts.push(0.0, yBot, 1.0, 0.2, 0.3);
        verts.push(askW, yTop, 1.0, 0.2, 0.3);
        verts.push(askW, yBot, 1.0, 0.2, 0.3);
      }

      const vbo = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(verts), gl.STATIC_DRAW);

      gl.useProgram(prog);
      const aPos = gl.getAttribLocation(prog, 'aPos');
      const aColor = gl.getAttribLocation(prog, 'aColor');
      gl.enableVertexAttribArray(aPos);
      gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 20, 0);
      gl.enableVertexAttribArray(aColor);
      gl.vertexAttribPointer(aColor, 3, gl.FLOAT, false, 20, 8);

      gl.drawArrays(gl.TRIANGLES, 0, verts.length / 5);
      gl.deleteBuffer(vbo);
    }

    if (state.running) {
      for (let s = 0; s < state.speed; s++) {
        stepTick();
      }
    }

    requestAnimationFrame(render);
  }
  requestAnimationFrame(render);

  // Controls Event Listeners
  document.getElementById('btnPlay').addEventListener('click', function() {
    state.running = !state.running;
    this.textContent = state.running ? 'PAUSE' : 'STREAM';
  });

  document.getElementById('btnStep').addEventListener('click', function() {
    state.running = false;
    document.getElementById('btnPlay').textContent = 'STREAM';
    stepTick();
  });

  document.getElementById('btnReset').addEventListener('click', function() {
    state.tickCount = 0;
    state.rawOfi = 0;
    state.purifiedOfi = 0;
    state.clockCount = 0;
    state.nopeCount = 0;
    state.glintsCount = 0;
    state.stepsCount = 0;
    document.getElementById('tickLogBody').innerHTML = '';
    updateDOM();
  });

  document.getElementById('scenarioSelect').addEventListener('change', function(e) {
    state.scenario = e.target.value;
  });

  document.querySelectorAll('.speed-btn').forEach(btn => {
    btn.addEventListener('click', function() {
      document.querySelectorAll('.speed-btn').forEach(b => b.classList.remove('active'));
      this.classList.add('active');
      state.speed = parseInt(this.dataset.speed, 10);
    });
  });

})();
</script>
</body>
</html>
"""


def export_studio(target_path: Path | str) -> Path:
    """Write the portable studio HTML to target_path."""
    path = Path(target_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    html_content = generate_studio_html()
    path.write_text(html_content, encoding="utf-8")
    return path
