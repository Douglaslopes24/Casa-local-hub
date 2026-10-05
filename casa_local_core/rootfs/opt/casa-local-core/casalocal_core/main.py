from __future__ import annotations

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from casalocal_core.config import settings
from casalocal_core.services.discovery import DiscoveryManager
from casalocal_core.services.registry import DeviceRegistry


DASHBOARD_HTML = """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Casa Local Hub</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0b0d10;
      --panel: rgba(255,255,255,.055);
      --line: rgba(255,255,255,.09);
      --text: #f5f7fa;
      --muted: #9ca6b3;
      --ok: #75dfa7;
      --warn: #ffd479;
      --accent: #dce7f7;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at 80% 0%, rgba(111,151,209,.14), transparent 32rem),
        radial-gradient(circle at 0% 100%, rgba(83,181,145,.08), transparent 28rem),
        var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    main { width: min(980px, calc(100% - 32px)); margin: 0 auto; padding: 54px 0 80px; }
    header { display: flex; justify-content: space-between; gap: 28px; align-items: flex-start; margin-bottom: 36px; }
    .eyebrow { color: var(--muted); font-size: 13px; letter-spacing: .12em; text-transform: uppercase; margin-bottom: 12px; }
    h1 { margin: 0; font-size: clamp(32px, 5vw, 52px); letter-spacing: -.045em; font-weight: 650; }
    .subtitle { color: var(--muted); margin-top: 12px; font-size: 16px; line-height: 1.55; }
    .status {
      display: flex; align-items: center; gap: 9px; white-space: nowrap;
      padding: 10px 13px; border: 1px solid var(--line); background: var(--panel);
      border-radius: 999px; color: #dce5ef; font-size: 13px;
    }
    .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--ok); box-shadow: 0 0 18px rgba(117,223,167,.65); }
    .hero {
      padding: 24px; border: 1px solid var(--line); border-radius: 24px; background: var(--panel);
      backdrop-filter: blur(18px); margin-bottom: 18px;
    }
    .hero-row { display:flex; justify-content:space-between; align-items:center; gap:20px; }
    .hero-title { font-size: 20px; font-weight: 620; margin-bottom: 7px; }
    .hero-copy { color: var(--muted); line-height: 1.5; font-size: 14px; }
    button {
      appearance:none; border:0; cursor:pointer; min-width:180px; padding:14px 18px; border-radius:14px;
      font-weight:650; font-size:14px; background:var(--accent); color:#111722; transition:.18s ease;
    }
    button:hover { transform:translateY(-1px); filter:brightness(1.04); }
    button:disabled { cursor:wait; opacity:.7; transform:none; }
    .summary { display:flex; gap:10px; flex-wrap:wrap; margin:18px 0; }
    .pill { border:1px solid var(--line); background:var(--panel); border-radius:999px; padding:9px 12px; color:var(--muted); font-size:13px; }
    .grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }
    .card { border:1px solid var(--line); background:var(--panel); border-radius:20px; padding:20px; min-height:170px; }
    .card-top { display:flex; justify-content:space-between; align-items:flex-start; gap:12px; }
    .device-name { font-size:18px; font-weight:620; letter-spacing:-.015em; }
    .vendor { color:var(--muted); font-size:13px; margin-top:4px; }
    .badge { border:1px solid var(--line); border-radius:999px; padding:6px 9px; font-size:11px; white-space:nowrap; }
    .badge.warn { color:var(--warn); }
    .badge.ok { color:var(--ok); }
    dl { display:grid; grid-template-columns:88px 1fr; gap:8px 12px; margin:20px 0 0; font-size:13px; }
    dt { color:var(--muted); }
    dd { margin:0; overflow-wrap:anywhere; }
    .empty { padding:32px 10px; text-align:center; color:var(--muted); }
    .error { margin-top:14px; color:#ffb6b6; font-size:13px; white-space:pre-wrap; }
    footer { color:#697482; font-size:12px; margin-top:34px; text-align:center; }
    @media (max-width:720px) {
      header { flex-direction:column; }
      .hero-row { flex-direction:column; align-items:stretch; }
      button { width:100%; }
      .grid { grid-template-columns:1fr; }
    }
  </style>
</head>
<body>
<main>
  <header>
    <div>
      <div class="eyebrow">Casa Local Core · v__VERSION__</div>
      <h1>Casa Local Hub</h1>
      <div class="subtitle">Sua casa. Seu controle. Local.</div>
    </div>
    <div class="status"><span class="dot"></span> Core online</div>
  </header>

  <section class="hero">
    <div class="hero-row">
      <div>
        <div class="hero-title">Descobrir dispositivos</div>
        <div class="hero-copy">Procura equipamentos compatíveis na sua rede local sem alterar nenhuma configuração.</div>
      </div>
      <button id="scanBtn" onclick="scan()">Buscar dispositivos</button>
    </div>
    <div id="error" class="error"></div>
  </section>

  <div id="summary" class="summary"></div>
  <section id="devices" class="grid"><div class="empty">Toque em “Buscar dispositivos” para começar.</div></section>

  <footer>Casa Local Hub · processamento local · Internet não necessária para a descoberta</footer>
</main>

<script>
const devicesEl = document.getElementById('devices');
const summaryEl = document.getElementById('summary');
const errorEl = document.getElementById('error');
const scanBtn = document.getElementById('scanBtn');

function el(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
}

function capabilityLabel(value) {
  if (value === 'local_control_ready') return ['Local pronto', 'ok'];
  if (value === 'credentials_required') return ['Chave local necessária', 'warn'];
  if (value === 'local_control_possible') return ['Controle local possível', 'ok'];
  return ['Encontrado', ''];
}

function renderDevices(devices) {
  devicesEl.replaceChildren();
  summaryEl.replaceChildren();

  const total = el('div', 'pill', devices.length + (devices.length === 1 ? ' dispositivo encontrado' : ' dispositivos encontrados'));
  summaryEl.appendChild(total);

  if (!devices.length) {
    devicesEl.appendChild(el('div', 'empty', 'Nenhum dispositivo compatível respondeu nesta busca.'));
    return;
  }

  for (const device of devices) {
    const card = el('article', 'card');
    const top = el('div', 'card-top');
    const left = el('div');
    const name = device.name || (device.kind === 'camera' ? 'Câmera local' : 'Dispositivo local');
    left.appendChild(el('div', 'device-name', name));
    left.appendChild(el('div', 'vendor', device.vendor || 'Fabricante não identificado'));

    const [label, badgeClass] = capabilityLabel(device.capability);
    const badge = el('span', 'badge ' + badgeClass, label);
    top.append(left, badge);
    card.appendChild(top);

    const details = document.createElement('dl');
    const rows = [
      ['Protocolo', device.protocol || '—'],
      ['Endereço', device.address || '—'],
      ['Porta', device.port ? String(device.port) : '—'],
      ['Tipo', device.kind || 'unknown']
    ];
    for (const [k, v] of rows) {
      details.append(el('dt', '', k), el('dd', '', v));
    }
    card.appendChild(details);
    devicesEl.appendChild(card);
  }
}

async function scan() {
  errorEl.textContent = '';
  scanBtn.disabled = true;
  scanBtn.textContent = 'Buscando…';
  devicesEl.replaceChildren(el('div', 'empty', 'Procurando dispositivos na rede local…'));
  summaryEl.replaceChildren();

  try {
    const response = await fetch('/api/v1/discovery', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({timeout: 6})
    });
    if (!response.ok) throw new Error('Falha HTTP ' + response.status);
    const data = await response.json();
    renderDevices(data.devices || []);
    if (data.errors && Object.keys(data.errors).length) {
      errorEl.textContent = 'Alguns módulos não responderam: ' + Object.keys(data.errors).join(', ');
    }
  } catch (err) {
    devicesEl.replaceChildren(el('div', 'empty', 'Não foi possível concluir a busca.'));
    errorEl.textContent = String(err);
  } finally {
    scanBtn.disabled = false;
    scanBtn.textContent = 'Buscar novamente';
  }
}
</script>
</body>
</html>"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    registry = DeviceRegistry()
    app.state.registry = registry
    app.state.discovery = DiscoveryManager(registry)
    yield


app = FastAPI(
    title="Casa Local Core",
    version=settings.version,
    description="Local-first discovery bridge for Casa Local Hub.",
    lifespan=lifespan,
)


@app.get("/", response_class=HTMLResponse)
async def root() -> HTMLResponse:
    return HTMLResponse(DASHBOARD_HTML.replace("__VERSION__", settings.version))


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "casa-local-core", "version": settings.version}


@app.get("/api/v1/status")
async def status() -> dict:
    return {
        "service": "casa-local-core",
        "version": settings.version,
        "known_devices": len(app.state.registry.all()),
        "adapters": list(app.state.discovery.adapters.keys()),
    }


@app.get("/api/v1/devices")
async def devices() -> dict:
    known = app.state.registry.all()
    return {
        "count": len(known),
        "devices": [device.model_dump(mode="json") for device in known],
    }


@app.post("/api/v1/discovery")
async def discovery(payload: dict | None = None) -> dict:
    payload = payload or {}
    timeout = float(payload.get("timeout", 6))
    protocols = payload.get("protocols")
    devices, errors = await app.state.discovery.discover(timeout=timeout, protocols=protocols)
    return {
        "count": len(devices),
        "devices": [device.model_dump(mode="json") for device in devices],
        "errors": errors,
    }


def run() -> None:
    uvicorn.run("casalocal_core.main:app", host=settings.host, port=settings.port, reload=False)


if __name__ == "__main__":
    run()
