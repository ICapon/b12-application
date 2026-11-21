// Minimal vanilla-JS client for the applications API. No build step.
const API = (new URLSearchParams(location.search).get("api") || "http://127.0.0.1:8000").replace(/\/$/, "");
const STAGES = ["New", "Phone screen scheduled", "Interview scheduled", "Hired", "Rejected"];
const $ = (id) => document.getElementById(id);
const state = { page: 1, totalPages: 1, filters: { page_size: 10 }, currentId: null };

$("api-label").textContent = `API: ${API}`;

// ---- helpers -------------------------------------------------------------
function el(tag, props = {}, ...children) {
  const node = Object.assign(document.createElement(tag), props); // textContent only: no HTML injection
  node.append(...children);
  return node;
}
const fmt = (iso) => new Date(iso).toLocaleString();

let toastTimer;
function toast(msg, isError = false) {
  const t = $("toast");
  t.textContent = msg;
  t.className = isError ? "error" : "";
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (t.hidden = true), 4000);
}

function log(method, url, reqBody, status, resBody) {
  const ok = typeof status === "number" && status < 400;
  const entry = el("div", { className: "log-entry" },
    el("b", {}, `${method} ${url} `),
    el("span", { className: ok ? "ok" : "bad" }, String(status)));
  if (reqBody !== undefined) entry.append(`\n→ ${JSON.stringify(reqBody)}`);
  entry.append(`\n← ${JSON.stringify(resBody)}`);
  $("log").prepend(entry);
}

// All calls go through here so every request/response lands in the log.
async function api(method, path, body) {
  const url = API + path;
  let res, data;
  try {
    res = await fetch(url, {
      method,
      headers: body ? { "Content-Type": "application/json" } : {},
      body: body ? JSON.stringify(body) : undefined,
    });
    data = await res.json().catch(() => null);
  } catch (err) {
    log(method, path, body, "network error", String(err));
    throw new Error(`Cannot reach the API at ${API}. Is it running, and is that port free?`);
  }
  log(method, path, body, res.status, data);
  if (!res.ok) {
    const d = data && data.detail;
    const msg = Array.isArray(d) ? d.map((e) => `${e.loc.slice(1).join(".")}: ${e.msg}`).join("; ") : d;
    throw new Error(msg || `HTTP ${res.status}`);
  }
  return data;
}

// Run an action; surface any error as a toast instead of an unhandled rejection.
const guard = (fn) => async (...args) => {
  try { await fn(...args); } catch (err) { toast(err.message, true); }
};

// ---- list view -----------------------------------------------------------
async function loadList() {
  const params = new URLSearchParams({ page: state.page, ...state.filters });
  const data = await api("GET", `/applications?${params}`);
  state.totalPages = Math.max(1, Math.ceil(data.total / data.page_size));

  const rows = $("rows");
  rows.replaceChildren();
  if (!data.items.length) {
    rows.append(el("tr", {}, el("td", { colSpan: 5, className: "muted" }, "No applications found")));
  }
  for (const a of data.items) {
    const tr = el("tr", {},
      el("td", {}, String(a.id)), el("td", {}, a.name), el("td", {}, a.email),
      el("td", {}, fmt(a.timestamp)), el("td", {}, a.receipt));
    tr.onclick = guard(() => openDetail(a.id));
    rows.append(tr);
  }
  $("page-info").textContent = `Page ${data.page} of ${state.totalPages} · ${data.total} total`;
  $("prev").disabled = data.page <= 1;
  $("next").disabled = data.page >= state.totalPages;
}

$("create-form").onsubmit = guard(async (e) => {
  e.preventDefault();
  const form = new FormData(e.target);
  const created = await api("POST", "/applications", Object.fromEntries(form));
  e.target.reset();
  toast(`Created #${created.id} · ${created.receipt}`);
  state.page = 1;
  await loadList();
});

$("filter-form").onsubmit = guard(async (e) => {
  e.preventDefault();
  state.filters = Object.fromEntries([...new FormData(e.target)].filter(([, v]) => v !== ""));
  state.page = 1;
  await loadList();
});
$("filter-reset").onclick = guard(async () => {
  $("filter-form").reset();
  state.filters = { page_size: 10 };
  state.page = 1;
  await loadList();
});
$("prev").onclick = guard(async () => { state.page--; await loadList(); });
$("next").onclick = guard(async () => { state.page++; await loadList(); });

// ---- detail view ---------------------------------------------------------
async function openDetail(id) {
  state.currentId = id;
  const [app, history] = await Promise.all([
    api("GET", `/applications/${id}`),
    api("GET", `/applications/${id}/history`),
  ]);
  $("list-view").hidden = true;
  $("detail-view").hidden = false;
  $("d-id").textContent = `#${app.id}`;

  const dl = $("d-fields");
  dl.replaceChildren();
  const fields = [
    ["Name", app.name], ["Email", app.email],
    ["Submitted", fmt(app.timestamp)], ["Receipt", app.receipt],
    ["Resume", app.resume_link], ["Repository", app.repository_link], ["Action run", app.action_run_link],
  ];
  for (const [k, v] of fields) if (v) dl.append(el("dt", {}, k), el("dd", {}, v));
  dl.append(el("dt", {}, "Current stage"), el("dd", {}, el("span", { className: `badge ${app.current_stage}` }, app.current_stage)));

  const select = $("stage-select");
  select.replaceChildren(...STAGES.map((s) => el("option", { value: s, selected: s === app.current_stage }, s)));

  const ol = $("history");
  ol.replaceChildren();
  for (const h of history) {
    const notes = h.notes.length
      ? el("ul", {}, ...h.notes.map((n) => el("li", {}, `${n.content} `, el("span", { className: "muted" }, `(${fmt(n.created_at)})`))))
      : el("span", { className: "muted" }, "No notes");
    ol.append(el("li", {}, el("b", {}, h.stage), el("span", { className: "muted" }, ` · ${fmt(h.entered_at)}`), el("br"), notes));
  }
}

$("stage-form").onsubmit = guard(async (e) => {
  e.preventDefault();
  const updated = await api("PUT", `/applications/${state.currentId}/stage`, { stage: $("stage-select").value });
  toast(`Stage is now "${updated.current_stage}"`);
  await openDetail(state.currentId);
});
$("note-form").onsubmit = guard(async (e) => {
  e.preventDefault();
  await api("POST", `/applications/${state.currentId}/notes`, { content: new FormData(e.target).get("content") });
  e.target.reset();
  toast("Note added");
  await openDetail(state.currentId);
});
$("back").onclick = guard(async () => {
  $("detail-view").hidden = true;
  $("list-view").hidden = false;
  await loadList();
});
$("log-clear").onclick = (e) => { e.preventDefault(); $("log").replaceChildren(); };

guard(loadList)();
