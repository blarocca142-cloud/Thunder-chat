(() => {
  const params = new URLSearchParams(location.search);
  const desktop = params.get("surface") === "desktop" || Boolean(window.thunderDesktop);
  const sameOrigin = location.protocol !== "file:";
  const stored = localStorage.getItem("thunder_server") || "";
  const state = {
    api: params.get("api") || stored || (sameOrigin ? "" : "http://127.0.0.1:8080"),
    tab: "chat",
    studio: "photo",
    chats: [],
    activeId: null,
    waiting: false,
    creations: [],
    status: null,
    style: "Cinematic",
    aspect: "1:1",
    duration: 8,
  };

  const $ = (id) => document.getElementById(id);
  const els = {
    app: $("app"),
    sidebar: $("sidebar"),
    chatList: $("chatList"),
    thread: $("thread"),
    draft: $("draft"),
    composer: $("composer"),
    server: $("server"),
    model: $("model"),
    statusPill: $("statusPill"),
    studioCanvas: $("studioCanvas"),
    prompt: $("studioPrompt"),
    videoPrompt: $("videoPrompt"),
    logs: $("logs"),
    toast: $("toast"),
    viewer: $("viewer"),
    jobTitle: $("jobTitle"),
    jobPrompt: $("jobPrompt"),
  };

  if (desktop) document.body.classList.add("desktop");
  els.server.value = state.api;
  loadChats();
  if (!state.chats.length) newChat(false);
  renderChats();
  renderThread();
  showTab("chat");

  function base() {
    return (state.api || "").replace(/\/$/, "");
  }
  function url(path) {
    return `${base()}${path}`;
  }
  async function api(path, opts) {
    const res = await fetch(url(path), opts);
    const text = await res.text();
    let data = text;
    try { data = JSON.parse(text); } catch {}
    if (!res.ok) throw new Error(typeof data === "string" ? data : data.detail || res.status);
    return data;
  }
  function saveChats() {
    localStorage.setItem("thunder_chats", JSON.stringify(state.chats));
  }
  function loadChats() {
    try { state.chats = JSON.parse(localStorage.getItem("thunder_chats") || "[]"); }
    catch { state.chats = []; }
  }
  function active() {
    return state.chats.find((c) => c.id === state.activeId);
  }
  function titleFrom(text) {
    const cleaned = (text || "").trim().replace(/\s+/g, " ");
    if (!cleaned) return "New chat";
    return cleaned.length <= 36 ? cleaned : `${cleaned.slice(0, 33)}…`;
  }
  function toast(msg) {
    els.toast.textContent = msg;
    els.toast.classList.remove("hidden");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => els.toast.classList.add("hidden"), 2800);
  }

  function newChat(focus) {
    const chat = { id: crypto.randomUUID(), title: "New chat", updatedAt: Date.now(), messages: [] };
    state.chats.unshift(chat);
    state.activeId = chat.id;
    saveChats();
    renderChats();
    renderThread();
    if (focus) els.draft.focus();
  }

  function renderChats() {
    els.chatList.innerHTML = "";
    if (!state.chats.length) {
      els.chatList.innerHTML = `<div class="side-label">Nothing saved yet.</div>`;
      return;
    }
    state.chats.forEach((chat) => {
      const row = document.createElement("div");
      row.className = `chat-item${chat.id === state.activeId ? " active" : ""}`;
      row.innerHTML = `<div class="meta"><div class="title"></div><div class="sub">${chat.messages.length} lines</div></div>
        <button class="icon-btn" data-act="del" title="Delete">✕</button>`;
      row.querySelector(".title").textContent = chat.title;
      row.addEventListener("click", (e) => {
        if (e.target.dataset.act === "del") {
          state.chats = state.chats.filter((c) => c.id !== chat.id);
          if (state.activeId === chat.id) state.activeId = state.chats[0]?.id || null;
          saveChats();
          renderChats();
          renderThread();
          return;
        }
        state.activeId = chat.id;
        renderChats();
        renderThread();
        showTab("chat");
        els.sidebar.classList.remove("open");
      });
      els.chatList.appendChild(row);
    });
  }

  function renderThread() {
    const chat = active();
    els.thread.innerHTML = "";
    if (!chat || !chat.messages.length) {
      els.thread.innerHTML = `<div class="empty-home">
        <img src="icon.png" alt="">
        <h2>THUNDER <span style="color:var(--gold);font-weight:300">AI</span></h2>
        <div>Ready when you are.</div>
      </div>`;
      return;
    }
    chat.messages.forEach((m) => {
      const d = document.createElement("div");
      d.className = `bubble ${m.who}`;
      d.textContent = m.text;
      els.thread.appendChild(d);
    });
    if (state.waiting) {
      const w = document.createElement("div");
      w.className = "bubble thunder";
      w.textContent = "Thunder is thinking…";
      els.thread.appendChild(w);
    }
    els.thread.scrollTop = els.thread.scrollHeight;
  }

  async function send(text, extra) {
    const chat = active() || (newChat(false), active());
    const msg = (text || els.draft.value).trim();
    if (!msg || state.waiting) return;
    els.draft.value = "";
    chat.messages.push({ who: "you", text: extra ? `${msg}\n\n${extra}` : msg, at: Date.now() });
    if (chat.title === "New chat") chat.title = titleFrom(msg);
    chat.updatedAt = Date.now();
    state.waiting = true;
    saveChats();
    renderChats();
    renderThread();
    try {
      const history = chat.messages.slice(0, -1).map((m) => ({
        role: m.who === "you" ? "user" : "assistant",
        content: m.text,
      }));
      const body = { message: extra ? `${msg}\n\n${extra}` : msg };
      if (desktop && history.length) body.messages = history;
      const data = await api("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      chat.messages.push({ who: "thunder", text: data.reply || JSON.stringify(data), at: Date.now() });
    } catch (err) {
      chat.messages.push({
        who: "thunder",
        text: state.api === "" && !sameOrigin
          ? `Can't reach Main. ${err.message}`
          : `Main offline. ${err.message}`,
        at: Date.now(),
      });
    }
    state.waiting = false;
    chat.updatedAt = Date.now();
    saveChats();
    renderChats();
    renderThread();
    refreshStatus();
  }

  function showTab(tab) {
    state.tab = tab;
    $("chatStage").classList.toggle("hidden", tab !== "chat");
    $("studioStage").classList.toggle("hidden", tab !== "studio");
    document.querySelectorAll("[data-tab]").forEach((el) => el.classList.toggle("on", el.dataset.tab === tab));
    if (tab === "studio") refreshCreations();
  }

  function showStudio(kind) {
    state.studio = kind;
    $("photoForm").classList.toggle("hidden", kind !== "photo");
    $("videoForm").classList.toggle("hidden", kind !== "video");
    document.querySelectorAll("[data-studio]").forEach((el) => el.classList.toggle("on", el.dataset.studio === kind));
    refreshCreations();
  }

  function mediaUrl(path) {
    if (!path) return "";
    if (/^https?:\/\//i.test(path)) return path;
    return url(path);
  }
  function videoPhase(item) {
    const reported = String(item.video_status || "").toLowerCase().trim();
    if (reported) return reported;
    if (item.kind !== "video") return "";
    if (item.video_url && !item.stub) return "done";
    if (item.stub) return "stub";
    return "processing";
  }
  function upsertCreation(item) {
    const i = state.creations.findIndex((c) => c.id === item.id);
    if (i >= 0) state.creations[i] = { ...state.creations[i], ...item };
    else state.creations.unshift(item);
    localStorage.setItem("thunder_creations", JSON.stringify(state.creations.slice(0, 80)));
  }
  const watchers = {};
  function watchVideo(id) {
    if (!id || watchers[id]) return;
    const started = Date.now();
    const tick = async () => {
      try {
        const fresh = await api(`/creations/${encodeURIComponent(id)}`);
        upsertCreation(fresh);
        const phase = videoPhase(fresh);
        if (phase === "processing" && Date.now() - started < 5 * 60 * 1000) {
          watchers[id] = setTimeout(tick, 5000);
          paintCreations();
          if (els.viewer.dataset.id === id) openViewer(id);
          return;
        }
        if (phase === "processing") {
          upsertCreation({ ...fresh, _timeout: true });
          toast("Taking longer than expected.");
        } else if (phase === "done") {
          toast(fresh.message || "Motion ready.");
        } else if (phase === "error") {
          toast(fresh.message || "Motion failed.");
        }
        delete watchers[id];
        paintCreations();
        if (els.viewer.dataset.id === id) openViewer(id);
      } catch {
        if (Date.now() - started < 5 * 60 * 1000) watchers[id] = setTimeout(tick, 5000);
        else delete watchers[id];
      }
    };
    watchers[id] = setTimeout(tick, 5000);
  }
  function cardHtml(item) {
    const src = mediaUrl(item.url);
    const phase = videoPhase(item);
    const badge = phase === "processing"
      ? " · rendering"
      : phase === "done"
        ? " · ready"
        : item.stub ? " · stub" : "";
    return `<article class="card" data-id="${item.id}">
      <img src="${src}" alt="">
      <div class="cap"><b>${escapeHtml(item.prompt)}</b><span>${item.kind} · ${item.style}${badge}</span></div>
    </article>`;
  }
  function escapeHtml(s) {
    return String(s || "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  async function refreshCreations() {
    try {
      const data = await api("/creations");
      state.creations = data.items || [];
    } catch {
      state.creations = JSON.parse(localStorage.getItem("thunder_creations") || "[]");
    }
    const filter = state.studio === "history" ? state.creations : state.creations.filter((i) => (
      state.studio === "photo" ? i.kind === "image" : state.studio === "video" ? i.kind === "video" : true
    ));
    paintCreations(filter);
    filter.filter((i) => videoPhase(i) === "processing").forEach((i) => watchVideo(i.id));
  }

  function paintCreations(filter) {
    const list = filter || (state.studio === "history" ? state.creations : state.creations.filter((i) => (
      state.studio === "photo" ? i.kind === "image" : state.studio === "video" ? i.kind === "video" : true
    )));
    if (!list.length) {
      els.studioCanvas.innerHTML = `<div class="empty-home"><div>Nothing on the wall yet.</div></div>`;
      return;
    }
    els.studioCanvas.innerHTML = `<div class="gallery">${list.map(cardHtml).join("")}</div>`;
    els.studioCanvas.querySelectorAll(".card").forEach((el) => {
      el.addEventListener("click", () => openViewer(el.dataset.id));
    });
  }

  function openViewer(id) {
    const item = state.creations.find((c) => c.id === id);
    if (!item) return;
    const phase = videoPhase(item);
    const poster = mediaUrl(item.url);
    const clip = mediaUrl(item.video_url);
    const media = item.kind === "video" && phase === "done" && clip
      ? `<video controls playsinline poster="${poster}" src="${clip}"></video>`
      : `<img src="${poster}" alt="">`;
    let status = item.message || "";
    if (item._timeout && phase === "processing") status = "Taking longer than expected.";
    else if (phase === "processing") status = status || "Rendering motion…";
    els.viewer.classList.remove("hidden");
    els.viewer.dataset.id = id;
    els.viewer.innerHTML = `<figure>
      ${media}
      <figcaption>
        <b>${escapeHtml(item.prompt)}</b>
        <div class="hint" style="color:var(--mute);margin:6px 0 12px">${escapeHtml(status)}</div>
        <div class="row">
          ${clip && phase === "done" ? `<a class="btn gold" href="${clip}" target="_blank" rel="noopener">Play</a>` : ""}
          <a class="btn${clip && phase === "done" ? "" : " gold"}" href="${poster}" download="${item.id}.png">Save</a>
          <button class="btn" data-share>Share</button>
          <button class="btn ghost" data-close>Close</button>
        </div>
      </figcaption>
    </figure>`;
    els.viewer.querySelector("[data-close]").onclick = () => {
      els.viewer.classList.add("hidden");
      delete els.viewer.dataset.id;
    };
    els.viewer.querySelector("[data-share]").onclick = async () => {
      const shareUrl = clip && phase === "done" ? clip : poster;
      if (navigator.share) {
        try { await navigator.share({ title: "Thunder", text: item.prompt, url: shareUrl }); }
        catch {}
      } else {
        await navigator.clipboard.writeText(shareUrl);
        toast("Link copied");
      }
    };
  }

  async function generate(kind) {
    const prompt = (kind === "image" ? els.prompt.value : els.videoPrompt.value).trim();
    if (!prompt) return toast("Give Thunder a prompt first.");
    const path = kind === "image" ? "/image" : "/video";
    const body = kind === "image"
      ? { prompt, style: state.style, aspect: state.aspect }
      : { prompt, style: state.style, duration: state.duration };
    toast(kind === "image" ? "Making a still…" : "Queuing motion…");
    try {
      const item = await api(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      upsertCreation(item);
      const phase = videoPhase(item);
      toast(phase === "processing" ? "Rendering motion…" : (item.message || "Done."));
      showStudio(kind === "image" ? "photo" : "video");
      await refreshCreations();
      openViewer(item.id);
      if (phase === "processing") watchVideo(item.id);
    } catch (err) {
      toast(`Studio missed: ${err.message}`);
    }
  }

  async function refreshStatus() {
    try {
      const st = await api("/status");
      state.status = st;
      const live = Boolean(st.ollama);
      els.statusPill.textContent = live ? `main · ${st.model || "ollama"}` : (state.api ? "main" : "local");
      els.statusPill.classList.toggle("live", live || Boolean(state.api));
      const maint = st.maintenance || {};
      const bar = $("maintBar");
      if (bar) {
        if (maint.active) {
          bar.classList.remove("hidden");
          const until = maint.until ? ` (until ${new Date(maint.until * 1000).toLocaleTimeString()})` : "";
          bar.textContent = (maint.message || "Thunder's down for maintenance.") + until;
        } else {
          bar.classList.add("hidden");
        }
      }
      if (desktop) {
        const models = await api("/models");
        els.model.innerHTML = (models.models || []).map((m) =>
          `<option value="${m.name}"${m.name === models.current ? " selected" : ""}>${m.name}</option>`
        ).join("") || `<option>${models.current || "none"}</option>`;
        const logs = await api("/logs");
        els.logs.textContent = (logs.lines || []).map((l) => `${l.kind}: ${l.message}`).join("\n") || "No events yet.";
      }
    } catch {
      els.statusPill.textContent = state.api ? "main offline" : "local";
      els.statusPill.classList.remove("live");
    }
  }

  $("newChat").onclick = () => newChat(true);
  $("tabChat").onclick = () => showTab("chat");
  $("tabStudio").onclick = () => showTab("studio");
  $("send").onclick = () => send();
  $("makePhoto").onclick = () => generate("image");
  $("makeVideo").onclick = () => generate("video");
  $("menu").onclick = () => els.sidebar.classList.toggle("open");
  els.draft.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey || !e.shiftKey && desktop)) {
      e.preventDefault();
      send();
    }
  });
  function rememberApi(next) {
    state.api = (next || "").trim().replace(/\/$/, "");
    localStorage.setItem("thunder_server", state.api);
    els.server.value = state.api;
    window.thunderDesktop?.setApi?.(state.api);
    refreshStatus();
    refreshCreations();
  }
  els.server.addEventListener("change", () => rememberApi(els.server.value));
  if (desktop && !state.api) {
    toast("Set Main URL in the sidebar — http://YOUR-MAIN-IP:8080");
  }
  els.model?.addEventListener("change", async () => {
    try {
      await api("/model", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model: els.model.value }),
      });
      toast(`Model ${els.model.value}`);
      refreshStatus();
    } catch (err) { toast(err.message); }
  });
  document.querySelectorAll("[data-studio]").forEach((el) => {
    el.onclick = () => showStudio(el.dataset.studio);
  });
  document.querySelectorAll("[data-style]").forEach((el) => {
    el.onclick = () => {
      state.style = el.dataset.style;
      document.querySelectorAll("[data-style]").forEach((c) => c.classList.toggle("on", c === el));
    };
  });
  document.querySelectorAll("[data-aspect]").forEach((el) => {
    el.onclick = () => {
      state.aspect = el.dataset.aspect;
      document.querySelectorAll("[data-aspect]").forEach((c) => c.classList.toggle("on", c === el));
    };
  });
  document.querySelectorAll("[data-dur]").forEach((el) => {
    el.onclick = () => {
      state.duration = Number(el.dataset.dur);
      document.querySelectorAll("[data-dur]").forEach((c) => c.classList.toggle("on", c === el));
    };
  });
  $("queueJob")?.addEventListener("click", async () => {
    try {
      const st = await api("/job", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: els.jobTitle.value || "overnight coding", prompt: els.jobPrompt.value }),
      });
      toast(`Queued ${st.job_id}`);
      refreshStatus();
    } catch (err) { toast(err.message); }
  });
  $("cancelJob")?.addEventListener("click", async () => {
    try {
      await api("/job/cancel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: state.status?.job_id || "" }),
      });
      toast("Cancel requested");
      refreshStatus();
    } catch (err) { toast(err.message); }
  });

  els.composer.addEventListener("dragover", (e) => {
    e.preventDefault();
    els.composer.classList.add("drop");
  });
  els.composer.addEventListener("dragleave", () => els.composer.classList.remove("drop"));
  els.composer.addEventListener("drop", async (e) => {
    e.preventDefault();
    els.composer.classList.remove("drop");
    const files = [...e.dataTransfer.files];
    if (!files.length) return;
    const bits = [];
    for (const file of files.slice(0, 4)) {
      if (file.size > 400_000 || !/text|json|javascript|python|markdown|xml/.test(file.type) && !/\.(md|txt|py|kt|js|ts|json|css|html)$/i.test(file.name)) {
        bits.push(`[file: ${file.name}, ${file.size} bytes — binary not inlined]`);
        continue;
      }
      bits.push(`--- ${file.name} ---\n${await file.text()}`);
    }
    send(els.draft.value || `Look at ${files.map((f) => f.name).join(", ")}`, bits.join("\n\n"));
  });

  $("pickFiles")?.addEventListener("click", async () => {
    if (window.thunderDesktop?.pickFiles) {
      const files = await window.thunderDesktop.pickFiles();
      if (files?.length) send("Review these files", files.map((f) => `--- ${f.name} ---\n${f.text}`).join("\n\n"));
    } else {
      $("fileInput").click();
    }
  });
  $("fileInput")?.addEventListener("change", async (e) => {
    const files = [...e.target.files];
    const bits = [];
    for (const file of files) bits.push(`--- ${file.name} ---\n${await file.text()}`);
    if (bits.length) send("Review these files", bits.join("\n\n"));
    e.target.value = "";
  });
  $("newWindow")?.addEventListener("click", () => window.thunderDesktop?.newWindow?.());
  $("mainUrl")?.addEventListener("click", () => {
    if (window.thunderDesktop?.openSettings) window.thunderDesktop.openSettings();
    else els.server.focus();
  });
  if (desktop && window.thunderDesktop?.getApi && !params.get("api")) {
    window.thunderDesktop.getApi().then((saved) => {
      if (saved && saved !== state.api) rememberApi(saved);
    });
  }
  $("exportFolder")?.addEventListener("click", async () => {
    if (!window.thunderDesktop?.pickFolder) {
      toast("Folder export is on the desktop app.");
      return;
    }
    const folder = await window.thunderDesktop.pickFolder();
    if (!folder) return;
    for (const item of state.creations.slice(0, 24)) {
      try {
        const poster = mediaUrl(item.url);
        if (poster) {
          const res = await fetch(poster);
          const buf = await res.arrayBuffer();
          const b64 = btoa(String.fromCharCode(...new Uint8Array(buf)));
          await window.thunderDesktop.saveBytes(folder, `${item.id}.png`, b64);
        }
        const clip = mediaUrl(item.video_url);
        if (clip && videoPhase(item) === "done") {
          const res = await fetch(clip);
          const buf = await res.arrayBuffer();
          const b64 = btoa(String.fromCharCode(...new Uint8Array(buf)));
          await window.thunderDesktop.saveBytes(folder, `${item.id}.mp4`, b64);
        }
      } catch {}
    }
    toast("Exported that folder.");
  });

  document.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "n") { e.preventDefault(); newChat(true); }
    if ((e.metaKey || e.ctrlKey) && e.key === "1") { e.preventDefault(); showTab("chat"); }
    if ((e.metaKey || e.ctrlKey) && e.key === "2") { e.preventDefault(); showTab("studio"); }
    if ((e.metaKey || e.ctrlKey) && e.key === ",") { e.preventDefault(); window.thunderDesktop?.openSettings?.() || els.server.focus(); }
    if ((e.metaKey || e.ctrlKey) && e.key === "b") { e.preventDefault(); els.sidebar.classList.toggle("open"); }
    if (e.key === "Escape") els.viewer.classList.add("hidden");
  });

  showStudio("photo");
  refreshStatus();
  setInterval(refreshStatus, 12000);
})();
