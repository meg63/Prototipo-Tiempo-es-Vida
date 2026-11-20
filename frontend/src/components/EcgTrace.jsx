import { useEffect, useRef } from 'react';

// Formato impreso estándar: 3 filas x 4 columnas de 2,5 s y una tira de ritmo (II) de 10 s.
// Papel a 25 mm/s y 10 mm/mV; cuadro pequeño = 1 mm, cuadro grande = 5 mm (0,2 s x 0,5 mV).
const LAYOUT = [
  ['I', 'aVR', 'V1', 'V4'],
  ['II', 'aVL', 'V2', 'V5'],
  ['III', 'aVF', 'V3', 'V6'],
];
const WIDTH_MM = 250;
const ROW_MM = 30;
const HEIGHT_MM = ROW_MM * 4;
const MM_PER_SECOND = 25;
const MM_PER_MV = 10;

function median(values) {
  const sorted = Array.from(values).sort((a, b) => a - b);
  return sorted[Math.floor(sorted.length / 2)];
}

function drawTrace(canvas, signal) {
  const styles = getComputedStyle(canvas);
  const color = (name, fallback) => styles.getPropertyValue(name).trim() || fallback;
  const cssWidth = canvas.clientWidth;
  if (!cssWidth) return;
  const mm = cssWidth / WIDTH_MM;
  const cssHeight = Math.round(HEIGHT_MM * mm);
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.round(cssWidth * dpr);
  canvas.height = Math.round(cssHeight * dpr);
  canvas.style.height = `${cssHeight}px`;

  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.fillStyle = color('--ecg-paper', '#FFFAF9');
  ctx.fillRect(0, 0, cssWidth, cssHeight);

  const line = (x0, y0, x1, y1) => { ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke(); };
  if (mm >= 2.2) {
    ctx.strokeStyle = color('--ecg-grid-minor', '#F7DCDA');
    ctx.lineWidth = 0.6;
    for (let i = 0; i <= WIDTH_MM; i += 1) if (i % 5) line(i * mm + 0.5, 0, i * mm + 0.5, cssHeight);
    for (let j = 0; j <= HEIGHT_MM; j += 1) if (j % 5) line(0, j * mm + 0.5, cssWidth, j * mm + 0.5);
  }
  ctx.strokeStyle = color('--ecg-grid-major', '#EAACA8');
  ctx.lineWidth = 1;
  for (let i = 0; i <= WIDTH_MM; i += 5) line(i * mm + 0.5, 0, i * mm + 0.5, cssHeight);
  for (let j = 0; j <= HEIGHT_MM; j += 5) line(0, j * mm + 0.5, cssWidth, j * mm + 0.5);

  const fs = signal.frecuencia_hz;
  const leadIndex = Object.fromEntries(signal.derivaciones.map((name, i) => [name, i]));
  // Se centra cada derivación en su mediana solo para dibujar (la línea de base varía).
  const centered = signal.mv.map((lead) => { const m = median(lead); return lead.map((v) => v - m); });
  const pxPerSample = (MM_PER_SECOND / fs) * mm;
  const pxPerMv = MM_PER_MV * mm;
  const traceColor = color('--ecg-trace', '#243C3B');

  ctx.save();
  ctx.beginPath();
  ctx.rect(0, 0, cssWidth, cssHeight);
  ctx.clip();
  ctx.strokeStyle = traceColor;
  ctx.lineWidth = Math.max(1, Math.min(1.6, mm * 0.32));
  ctx.lineJoin = 'round';
  ctx.lineCap = 'round';
  const plot = (lead, from, to, x0, baseline) => {
    const data = centered[leadIndex[lead]];
    if (!data) return;
    ctx.beginPath();
    for (let s = from; s < to && s < data.length; s += 1) {
      const x = x0 + (s - from) * pxPerSample;
      const y = baseline - data[s] * pxPerMv;
      if (s === from) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.stroke();
  };
  const segment = Math.round(2.5 * fs);
  LAYOUT.forEach((row, r) => row.forEach((lead, c) => {
    plot(lead, c * segment, (c + 1) * segment, c * 62.5 * mm, (r * ROW_MM + ROW_MM / 2) * mm);
  }));
  plot('II', 0, signal.mv[0].length, 0, (3 * ROW_MM + ROW_MM / 2) * mm);
  ctx.restore();

  // Separadores entre columnas y nombres de derivación.
  ctx.strokeStyle = traceColor;
  ctx.lineWidth = 1.2;
  for (let c = 1; c < 4; c += 1) {
    for (let r = 0; r < 3; r += 1) {
      const x = c * 62.5 * mm;
      const y = (r * ROW_MM + ROW_MM / 2) * mm;
      line(x, y - 2.5 * mm, x, y + 2.5 * mm);
    }
  }
  const fontSize = Math.max(10, Math.min(14, mm * 3.2));
  ctx.font = `700 ${fontSize}px system-ui, -apple-system, "Segoe UI", sans-serif`;
  ctx.textBaseline = 'top';
  const label = (text, x, y) => {
    const w = ctx.measureText(text).width;
    ctx.globalAlpha = 0.85;
    ctx.fillStyle = color('--ecg-paper', '#FFFAF9');
    ctx.fillRect(x - 3, y - 2, w + 6, fontSize + 4);
    ctx.globalAlpha = 1;
    ctx.fillStyle = color('--ecg-label', '#647775');
    ctx.fillText(text, x, y);
  };
  LAYOUT.forEach((row, r) => row.forEach((lead, c) => label(lead, c * 62.5 * mm + 1.5 * mm, r * ROW_MM * mm + 1.5 * mm)));
  label('II · ritmo 10 s', 1.5 * mm, 3 * ROW_MM * mm + 1.5 * mm);
}

export default function EcgTrace({ signal }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !signal) return undefined;
    drawTrace(canvas, signal);
    const observer = new ResizeObserver(() => drawTrace(canvas, signal));
    observer.observe(canvas);
    return () => observer.disconnect();
  }, [signal]);

  return (
    <div className="tv-ecg-trace-scroll">
      <canvas
        ref={canvasRef}
        className="tv-ecg-trace"
        role="img"
        aria-label="Trazado del electrocardiograma: 12 derivaciones en formato estándar y tira de ritmo de 10 segundos en la derivación II"
      />
    </div>
  );
}
