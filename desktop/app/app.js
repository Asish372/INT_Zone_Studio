(() => {
  "use strict";

  const API = "";
  const SESSION_KEY = "polygon_workspace_session_id";

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  const welcomeScreen = $("#welcome-screen");
  const workspaceScreen = $("#workspace-screen");
  const canvas = $("#canvas");
  const ctx = canvas.getContext("2d");
  const minimap = $("#minimap");
  const miniCtx = minimap.getContext("2d");
  const wrap = $("#canvas-wrap");

  let sessionId = localStorage.getItem(SESSION_KEY) || "";
  let scene = null;
  let bounds = null;
  let tool = "select";
  let scale = 1;
  let offsetX = 0;
  let offsetY = 0;
  let panning = false;
  let lastX = 0;
  let lastY = 0;
  let selectedId = null;
  let rafPending = false;

  const layers = {
    cad: true,
    auto: true,
    seed: true,
    deleted: true,
  };

  function headers(json = false) {
    const h = { "X-Session-Id": sessionId };
    if (json) h["Content-Type"] = "application/json";
    return h;
  }

  async function ensureSession() {
    if (sessionId) return;
    const res = await fetch(`${API}/session`, { method: "POST" });
    const data = await res.json();
    sessionId = data.session_id;
    localStorage.setItem(SESSION_KEY, sessionId);
  }

  function showWorkspace() {
    welcomeScreen.classList.add("hidden");
    workspaceScreen.classList.remove("hidden");
    resize();
  }

  function showWelcome() {
    workspaceScreen.classList.add("hidden");
    welcomeScreen.classList.remove("hidden");
  }

  function updateStats(counts) {
    if (!counts) return;
    $("#stat-detected").textContent = counts.detected ?? 0;
    $("#stat-seed").textContent = counts.seed_added ?? 0;
    $("#stat-total").textContent = counts.total ?? 0;
  }

  function formatTime(iso) {
    if (!iso) return "";
    try {
      return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch {
      return "";
    }
  }

  function renderActions(actions) {
    const log = $("#action-log");
    log.innerHTML = "";
    (actions || []).slice(0, 12).forEach((a) => {
      const li = document.createElement("li");
      li.className = a.kind || "info";
      li.innerHTML = `${a.message}<span class="time">${formatTime(a.at)}</span>`;
      log.appendChild(li);
    });
  }

  function renderPolygonInfo(poly) {
    const card = $("#polygon-info");
    if (!poly) {
      card.className = "info-card empty";
      card.innerHTML = "<p class=\"muted\">Select a polygon or add a seed</p>";
      return;
    }
    card.className = "info-card";
    const srcLabel = poly.source === "seed" ? "Seed Recovered" : "Auto Detected";
    const srcClass = poly.source === "seed" ? "green" : "";
    const statusLabel = poly.status === "deleted" ? "Deleted" : "Active";
    const statusClass = poly.status === "deleted" ? "red" : "green";
    card.innerHTML = `
      <div class="info-row"><span class="label">ID</span><span class="value">#${poly.id}</span></div>
      <div class="info-row"><span class="label">Source</span><span class="value ${srcClass}">${srcLabel}</span></div>
      <div class="info-row"><span class="label">Area</span><span class="value">${(poly.area_m2 ?? 0).toFixed(2)} m²</span></div>
      <div class="info-row"><span class="label">Perimeter</span><span class="value">${(poly.perimeter_m ?? 0).toFixed(2)} m</span></div>
      <div class="info-row"><span class="label">Status</span><span class="value ${statusClass}">${statusLabel}</span></div>
    `;
  }

  function computeBounds(sc) {
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    const consider = (x, y) => {
      minX = Math.min(minX, x); minY = Math.min(minY, y);
      maxX = Math.max(maxX, x); maxY = Math.max(maxY, y);
    };
    for (const line of sc.cad_lines || []) {
      consider(line[0], line[1]); consider(line[2], line[3]);
    }
    for (const poly of sc.polygons || []) {
      for (const [x, y] of poly.ring || []) consider(x, y);
    }
    if (!isFinite(minX)) return { minX: 0, minY: 0, maxX: 1, maxY: 1 };
    const padX = (maxX - minX) * 0.02 || 1;
    const padY = (maxY - minY) * 0.02 || 1;
    return { minX: minX - padX, minY: minY - padY, maxX: maxX + padX, maxY: maxY + padY };
  }

  function worldToScreen(x, y) {
    return [x * scale + offsetX, -y * scale + offsetY];
  }

  function screenToWorld(sx, sy) {
    return [(sx - offsetX) / scale, -(sy - offsetY) / scale];
  }

  function getViewportWorldBounds() {
    const w = wrap.clientWidth;
    const h = wrap.clientHeight;
    const [x0, y0] = screenToWorld(0, 0);
    const [x1, y1] = screenToWorld(w, h);
    return {
      minX: Math.min(x0, x1),
      maxX: Math.max(x0, x1),
      minY: Math.min(y0, y1),
      maxY: Math.max(y0, y1),
    };
  }

  function segmentInView(x1, y1, x2, y2, vp) {
    const minX = Math.min(x1, x2);
    const maxX = Math.max(x1, x2);
    const minY = Math.min(y1, y2);
    const maxY = Math.max(y1, y2);
    return !(maxX < vp.minX || minX > vp.maxX || maxY < vp.minY || minY > vp.maxY);
  }

  function polyInView(ring, vp) {
    for (const [x, y] of ring) {
      if (x >= vp.minX && x <= vp.maxX && y >= vp.minY && y <= vp.maxY) return true;
    }
    return false;
  }

  function fitToView() {
    if (!scene || !bounds) return;
    const w = wrap.clientWidth;
    const h = wrap.clientHeight;
    const bw = bounds.maxX - bounds.minX;
    const bh = bounds.maxY - bounds.minY;
    scale = Math.min(w / bw, h / bh) * 0.92;
    offsetX = (w - bw * scale) / 2 - bounds.minX * scale;
    offsetY = (h + bh * scale) / 2 + bounds.minY * scale;
    requestDraw();
  }

  function drawGrid(w, h) {
    const step = 50 * scale;
    if (step < 8) return;
    ctx.strokeStyle = "rgba(255,255,255,0.03)";
    ctx.lineWidth = 1;
    const startX = offsetX % step;
    for (let x = startX; x < w; x += step) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.stroke();
    }
    const startY = offsetY % step;
    for (let y = startY; y < h; y += step) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }
  }

  function drawMain() {
    const w = wrap.clientWidth;
    const h = wrap.clientHeight;
    ctx.fillStyle = "#0d0d10";
    ctx.fillRect(0, 0, w, h);
    drawGrid(w, h);
    if (!scene) return;

    const vp = getViewportWorldBounds();
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    if (layers.cad) {
      ctx.strokeStyle = "rgba(180, 180, 190, 0.35)";
      ctx.lineWidth = 0.6;
      ctx.beginPath();
      for (const [x1, y1, x2, y2] of scene.cad_lines || []) {
        if (!segmentInView(x1, y1, x2, y2, vp)) continue;
        const [sx1, sy1] = worldToScreen(x1, y1);
        const [sx2, sy2] = worldToScreen(x2, y2);
        ctx.moveTo(sx1, sy1);
        ctx.lineTo(sx2, sy2);
      }
      ctx.stroke();
    }

    for (const poly of scene.polygons || []) {
      const ring = poly.ring || [];
      if (ring.length < 2) continue;
      const isDeleted = poly.status === "deleted";
      const isSeed = poly.source === "seed";
      if (isDeleted && !layers.deleted) continue;
      if (isSeed && !layers.seed) continue;
      if (!isSeed && !isDeleted && !layers.auto) continue;
      if (!polyInView(ring, vp) && poly.id !== selectedId) continue;

      const isSelected = poly.id === selectedId;
      if (isDeleted) {
        ctx.strokeStyle = "#ef4444";
        ctx.setLineDash([5, 4]);
        ctx.lineWidth = 1.2;
      } else if (isSelected) {
        ctx.strokeStyle = "#3b82f6";
        ctx.setLineDash([]);
        ctx.lineWidth = 2.5;
      } else if (isSeed) {
        ctx.strokeStyle = "#22c55e";
        ctx.setLineDash([7, 4]);
        ctx.lineWidth = 1.8;
      } else {
        ctx.strokeStyle = "rgba(255,255,255,0.85)";
        ctx.setLineDash([]);
        ctx.lineWidth = 1;
      }

      ctx.beginPath();
      const [fx, fy] = worldToScreen(ring[0][0], ring[0][1]);
      ctx.moveTo(fx, fy);
      for (let i = 1; i < ring.length; i++) {
        const [sx, sy] = worldToScreen(ring[i][0], ring[i][1]);
        ctx.lineTo(sx, sy);
      }
      ctx.closePath();
      ctx.stroke();

      if (isSelected && ring.length > 0) {
        const cx = ring.reduce((s, p) => s + p[0], 0) / ring.length;
        const cy = ring.reduce((s, p) => s + p[1], 0) / ring.length;
        const [tx, ty] = worldToScreen(cx, cy);
        ctx.fillStyle = "#22c55e";
        ctx.font = "11px sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(`#${poly.id}`, tx, ty - 8);
      }
    }
    ctx.setLineDash([]);
    drawMinimap();
  }

  function drawMinimap() {
    if (!scene || !bounds) return;
    const mw = minimap.width;
    const mh = minimap.height;
    miniCtx.fillStyle = "#141418";
    miniCtx.fillRect(0, 0, mw, mh);
    const bw = bounds.maxX - bounds.minX;
    const bh = bounds.maxY - bounds.minY;
    const ms = Math.min(mw / bw, mh / bh) * 0.9;
    const mx = (mw - bw * ms) / 2 - bounds.minX * ms;
    const my = (mh + bh * ms) / 2 + bounds.minY * ms;

    miniCtx.strokeStyle = "rgba(120,120,130,0.5)";
    miniCtx.lineWidth = 0.5;
    miniCtx.beginPath();
    for (const [x1, y1, x2, y2] of (scene.cad_lines || []).slice(0, 8000)) {
      miniCtx.moveTo(x1 * ms + mx, -y1 * ms + my);
      miniCtx.lineTo(x2 * ms + mx, -y2 * ms + my);
    }
    miniCtx.stroke();

    miniCtx.strokeStyle = "rgba(255,255,255,0.4)";
    for (const poly of scene.polygons || []) {
      if (poly.status === "deleted") continue;
      const ring = poly.ring || [];
      if (ring.length < 2) continue;
      miniCtx.beginPath();
      miniCtx.moveTo(ring[0][0] * ms + mx, -ring[0][1] * ms + my);
      for (let i = 1; i < ring.length; i++) {
        miniCtx.lineTo(ring[i][0] * ms + mx, -ring[i][1] * ms + my);
      }
      miniCtx.closePath();
      miniCtx.stroke();
    }

    const w = wrap.clientWidth;
    const h = wrap.clientHeight;
    const [wx0, wy0] = screenToWorld(0, 0);
    const [wx1, wy1] = screenToWorld(w, h);
    const vx0 = Math.min(wx0, wx1) * ms + mx;
    const vx1 = Math.max(wx0, wx1) * ms + mx;
    const vy0 = -Math.max(wy0, wy1) * ms + my;
    const vy1 = -Math.min(wy0, wy1) * ms + my;
    miniCtx.strokeStyle = "#3b82f6";
    miniCtx.lineWidth = 1.5;
    miniCtx.strokeRect(vx0, vy0, vx1 - vx0, vy1 - vy0);
  }

  function requestDraw() {
    if (rafPending) return;
    rafPending = true;
    requestAnimationFrame(() => {
      rafPending = false;
      drawMain();
    });
  }

  function resize() {
    const dpr = window.devicePixelRatio || 1;
    const w = wrap.clientWidth;
    const h = wrap.clientHeight;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = w + "px";
    canvas.style.height = h + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    requestDraw();
  }

  function setTool(name) {
    tool = name;
    $$(".tool-btn").forEach((b) => b.classList.toggle("active", b.dataset.tool === name));
    wrap.className = "canvas-wrap";
    if (name === "pan") wrap.classList.add("tool-pan");
    if (name === "add") wrap.classList.add("tool-add");
    if (name === "select") wrap.classList.add("tool-select");
    $("#seed-hint").classList.toggle("hidden", name !== "add");
  }

  function findPolygonAt(wx, wy) {
    if (!scene) return null;
    let best = null;
    let bestArea = Infinity;
    for (const poly of scene.polygons || []) {
      if (poly.status === "deleted") continue;
      const ring = poly.ring;
      if (!ring || ring.length < 3) continue;
      if (!pointInRing(wx, wy, ring)) continue;
      const area = shoelaceArea(ring);
      if (area < bestArea) {
        bestArea = area;
        best = poly;
      }
    }
    return best;
  }

  function shoelaceArea(ring) {
    let a = 0;
    for (let i = 0; i < ring.length; i++) {
      const j = (i + 1) % ring.length;
      a += ring[i][0] * ring[j][1] - ring[j][0] * ring[i][1];
    }
    return Math.abs(a / 2);
  }

  function pointInRing(x, y, ring) {
    let inside = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const xi = ring[i][0], yi = ring[i][1];
      const xj = ring[j][0], yj = ring[j][1];
      if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) {
        inside = !inside;
      }
    }
    return inside;
  }

  async function selectPolygon(id) {
    selectedId = id;
    const res = await fetch(`${API}/select`, {
      method: "POST",
      headers: headers(true),
      body: JSON.stringify({ polygon_id: id }),
    });
    const data = await res.json();
    if (res.ok && data.selected) {
      renderPolygonInfo(data.selected);
    } else if (id === null) {
      renderPolygonInfo(null);
    }
    requestDraw();
  }

  async function uploadFile(file) {
    await ensureSession();
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch(`${API}/upload`, { method: "POST", headers: headers(), body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Upload failed");

    sessionId = data.session_id || sessionId;
    localStorage.setItem(SESSION_KEY, sessionId);
    scene = data.scene;
    bounds = computeBounds(scene);
    selectedId = null;

    $("#top-filename").textContent = data.source_file;
    $("#status-file").textContent = data.source_file;
    $("#status-units").textContent = data.unit_label || "mm";
    updateStats(data.counts);
    renderActions(data.actions);
    renderPolygonInfo(null);

    showWorkspace();
    fitToView();
  }

  async function recoverAt(wx, wy) {
    const res = await fetch(`${API}/recover`, {
      method: "POST",
      headers: headers(true),
      body: JSON.stringify({ x: wx, y: wy }),
    });
    const data = await res.json();
    if (!res.ok) {
      renderActions([{ message: data.detail || "Recovery failed", kind: "warn", at: new Date().toISOString() }, ...($("#action-log").children.length ? [] : [])]);
      return;
    }
    scene = data.scene;
    bounds = computeBounds(scene);
    updateStats(data.counts);
    renderActions(data.actions);
    selectedId = data.polygon?.id ?? null;
    renderPolygonInfo(data.selected || data.polygon);
    requestDraw();
  }

  async function deleteSelected() {
    if (!selectedId) return;
    const res = await fetch(`${API}/polygon/${selectedId}/delete`, {
      method: "POST",
      headers: headers(),
    });
    const data = await res.json();
    if (!res.ok) return;
    scene = data.scene;
    updateStats(data.counts);
    renderActions(data.actions);
    selectedId = null;
    renderPolygonInfo(null);
    requestDraw();
  }

  function openExportModal() {
    $("#export-modal").classList.remove("hidden");
  }

  function closeExportModal() {
    $("#export-modal").classList.add("hidden");
  }

  async function doExport(formats) {
    closeExportModal();
    const res = await fetch(`${API}/export`, {
      method: "POST",
      headers: headers(true),
      body: JSON.stringify({ formats, use_timestamp: true }),
    });
    const data = await res.json();
    if (!res.ok) return;
    renderActions(data.actions);
    const paths = Object.values(data.paths || {}).join(", ");
    renderActions([
      { message: `Saved: ${paths}`, kind: "success", at: new Date().toISOString() },
      ...(data.actions || []),
    ]);
  }

  function bindUpload(inputEl) {
    inputEl.addEventListener("change", async (e) => {
      const file = e.target.files?.[0];
      if (!file) return;
      try {
        await uploadFile(file);
      } catch (err) {
        alert(err.message);
      }
      inputEl.value = "";
    });
  }

  bindUpload($("#welcome-file-input"));
  $("#welcome-upload-btn").addEventListener("click", () => $("#welcome-file-input").click());
  $("#browse-btn").addEventListener("click", () => $("#welcome-file-input").click());

  const dropZone = $("#drop-zone");
  dropZone.addEventListener("dragover", (e) => { e.preventDefault(); dropZone.classList.add("dragover"); });
  dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
  dropZone.addEventListener("drop", async (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    const file = e.dataTransfer.files?.[0];
    if (!file) return;
    try { await uploadFile(file); } catch (err) { alert(err.message); }
  });

  $$(".tool-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const t = btn.dataset.tool;
      if (t === "fit") { fitToView(); return; }
      setTool(t);
    });
  });

  $("#top-save-btn").addEventListener("click", openExportModal);
  $("#modal-close").addEventListener("click", closeExportModal);
  $("#modal-cancel").addEventListener("click", closeExportModal);
  $(".modal-backdrop").addEventListener("click", closeExportModal);
  $$(".export-option").forEach((btn) => {
    btn.addEventListener("click", () => {
      const fmts = btn.dataset.formats.split(",");
      doExport(fmts);
    });
  });

  $("#zoom-in").addEventListener("click", () => zoomAt(wrap.clientWidth / 2, wrap.clientHeight / 2, 1.2));
  $("#zoom-out").addEventListener("click", () => zoomAt(wrap.clientWidth / 2, wrap.clientHeight / 2, 0.82));
  $("#zoom-fit").addEventListener("click", fitToView);

  function zoomAt(mx, my, factor) {
    const [wx, wy] = screenToWorld(mx, my);
    scale *= factor;
    const [sx, sy] = worldToScreen(wx, wy);
    offsetX += mx - sx;
    offsetY += my - sy;
    requestDraw();
  }

  wrap.addEventListener("wheel", (e) => {
    e.preventDefault();
    if (!scene) return;
    const rect = canvas.getBoundingClientRect();
    const factor = e.deltaY < 0 ? 1.1 : 0.9;
    zoomAt(e.clientX - rect.left, e.clientY - rect.top, factor);
  }, { passive: false });

  wrap.addEventListener("mousedown", (e) => {
    if (!scene) return;
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const [wx, wy] = screenToWorld(mx, my);

    if (tool === "add" && e.button === 0) {
      recoverAt(wx, wy);
      return;
    }
    if (tool === "select" && e.button === 0) {
      const hit = findPolygonAt(wx, wy);
      selectPolygon(hit ? hit.id : null);
      return;
    }
    if (tool === "pan" && e.button === 0) {
      panning = true;
      lastX = mx;
      lastY = my;
      wrap.classList.add("panning");
    }
  });

  window.addEventListener("mouseup", () => {
    panning = false;
    wrap.classList.remove("panning");
  });

  wrap.addEventListener("mousemove", (e) => {
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const [wx, wy] = screenToWorld(mx, my);
    $("#status-coords").textContent = `X: ${wx.toFixed(1)}, Y: ${wy.toFixed(1)}`;

    if (!panning) return;
    offsetX += mx - lastX;
    offsetY += my - lastY;
    lastX = mx; lastY = my;
    requestDraw();
  });

  ["layer-cad", "layer-auto", "layer-seed", "layer-deleted"].forEach((id) => {
    $(`#${id}`).addEventListener("change", (e) => {
      const key = id.replace("layer-", "");
      layers[key] = e.target.checked;
      requestDraw();
    });
  });

  window.addEventListener("keydown", (e) => {
    if (e.target.tagName === "INPUT") return;
    if (e.key === "s" || e.key === "S") setTool("select");
    if (e.key === "a" || e.key === "A") setTool("add");
    if (e.key === "p" || e.key === "P") setTool("pan");
    if (e.key === "f" || e.key === "F") fitToView();
    if (e.key === "Delete") deleteSelected();
    if (e.ctrlKey && e.key === "s") { e.preventDefault(); openExportModal(); }
  });

  window.addEventListener("resize", resize);
  ensureSession();
  setTool("select");
  resize();
})();
