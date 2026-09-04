(function () {
  "use strict";
  const script = document.currentScript;
  const token = script && script.dataset.token;
  const base = new URL(script.src).origin;
  if (!token) return console.error("MB Future Tech AI Chatbot widget: data-token is required.");

  fetch(base + "/widget/public/" + encodeURIComponent(token) + "/config")
    .then(function (response) {
      if (!response.ok) throw new Error("Widget is unavailable.");
      return response.json();
    })
    .then(mount)
    .catch(function (error) { console.error("MB Future Tech AI Chatbot widget:", error.message); });

  function mount(config) {
    const side = config.position === "left" ? "left" : "right";
    const host = document.createElement("div");
    host.style.cssText = "position:fixed;bottom:20px;" + side + ":20px;z-index:2147483647";
    const root = host.attachShadow({ mode: "open" });
    root.innerHTML = `
      <style>
        *{box-sizing:border-box}button,input{font:inherit}
        .launch{width:58px;height:58px;border:0;border-radius:50%;color:white;background:${config.primary_color};box-shadow:0 8px 28px #0004;cursor:pointer;font-size:25px}
        .panel{display:none;width:min(360px,calc(100vw - 32px));height:500px;max-height:calc(100vh - 100px);margin-bottom:12px;background:white;border-radius:18px;box-shadow:0 18px 55px #0004;overflow:hidden;font:14px system-ui;color:#172033}
        .panel.open{display:flex;flex-direction:column}.head{padding:16px;color:white;background:${config.primary_color};font-weight:700}
        .messages{flex:1;overflow:auto;padding:14px;background:#f6f7fb}.msg{max-width:85%;padding:10px 12px;margin:7px 0;border-radius:13px;white-space:pre-wrap}
        .bot{background:white;border:1px solid #e5e7eb}.user{margin-left:auto;background:${config.primary_color};color:white}
        form{display:flex;gap:8px;padding:12px;border-top:1px solid #e5e7eb}input{flex:1;min-width:0;border:1px solid #d1d5db;border-radius:10px;padding:10px}
        .send{border:0;border-radius:10px;padding:0 14px;color:white;background:${config.primary_color};cursor:pointer}
      </style>
      <section class="panel" aria-label="${escapeHtml(config.title)}">
        <div class="head">${escapeHtml(config.title)}</div>
        <div class="messages"><div class="msg bot">${escapeHtml(config.welcome_message)}</div></div>
        <form><input aria-label="Message" placeholder="Type a message…" maxlength="4000"><button class="send">Send</button></form>
      </section>
      <button class="launch" aria-label="Open chat">✦</button>`;
    document.body.appendChild(host);
    const panel = root.querySelector(".panel");
    const launch = root.querySelector(".launch");
    const form = root.querySelector("form");
    const input = root.querySelector("input");
    const messages = root.querySelector(".messages");
    let sessionId = sessionStorage.getItem("aura_widget_session_" + token);
    launch.onclick = function () { panel.classList.toggle("open"); if (panel.classList.contains("open")) input.focus(); };
    form.onsubmit = async function (event) {
      event.preventDefault();
      const text = input.value.trim();
      if (!text) return;
      add(text, "user"); input.value = ""; input.disabled = true;
      try {
        const response = await fetch(base + "/widget/public/" + encodeURIComponent(token) + "/chat", {
          method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({text: text, session_id: sessionId, language: document.documentElement.lang || "english"})
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Unable to send message.");
        sessionId = data.session_id;
        sessionStorage.setItem("aura_widget_session_" + token, sessionId);
        add(data.reply, "bot");
      } catch (error) { add(error.message, "bot"); }
      input.disabled = false; input.focus();
    };
    function add(text, type) {
      const item = document.createElement("div");
      item.className = "msg " + type; item.textContent = text;
      messages.appendChild(item); messages.scrollTop = messages.scrollHeight;
    }
  }
  function escapeHtml(value) {
    const div = document.createElement("div"); div.textContent = value; return div.innerHTML;
  }
})();
