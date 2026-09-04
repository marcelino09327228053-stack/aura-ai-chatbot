(function () {
  if (!document.getElementById("aura-notification-styles")) {
    const style = document.createElement("style");
    style.id = "aura-notification-styles";
    style.textContent = `
      .aura-global-toasts{position:fixed;top:18px;left:50%;z-index:100000;display:grid;gap:8px;width:min(440px,calc(100vw - 32px));transform:translateX(-50%);pointer-events:none}
      .aura-global-toast{display:grid;grid-template-columns:1fr auto;align-items:center;gap:12px;padding:13px 14px;border:1px solid rgba(148,163,184,.28);border-left:4px solid #60a5fa;border-radius:13px;background:#111827;color:#f8fafc;box-shadow:0 18px 55px rgba(0,0,0,.5);pointer-events:auto;animation:auraToastIn .2s ease-out}
      .aura-global-toast.error{border-left-color:#ef6464}.aura-global-toast.success{border-left-color:#48c78e}
      .aura-global-toast button{width:28px;height:28px;padding:0;border:0;background:transparent;color:#aab4c4;cursor:pointer}
      .aura-global-toast.leaving{opacity:0;transform:translateY(-8px);transition:.18s}
      .aura-global-prompt{position:fixed;inset:0;z-index:100010;display:grid;place-items:center;padding:18px;background:rgba(0,0,0,.7);backdrop-filter:blur(7px)}
      .aura-global-prompt[hidden]{display:none!important}.aura-global-prompt form{width:min(480px,100%);padding:20px;border:1px solid rgba(148,163,184,.28);border-radius:18px;background:#111827;color:#f8fafc;box-shadow:0 24px 80px rgba(0,0,0,.55)}
      .aura-global-prompt h3{margin:0 0 8px}.aura-global-prompt p{margin:0 0 14px;color:#aab4c4;white-space:pre-wrap}.aura-global-prompt input,.aura-global-prompt textarea{width:100%;box-sizing:border-box;padding:11px;border:1px solid rgba(148,163,184,.28);border-radius:10px;background:#0b1220;color:#f8fafc}
      .aura-global-prompt textarea{min-height:150px;resize:vertical}.aura-global-prompt-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:14px}.aura-global-prompt-actions button{padding:10px 16px;border:0;border-radius:10px;background:#334155;color:#fff;cursor:pointer}.aura-global-prompt-actions button:last-child{background:#3b82f6}
      @keyframes auraToastIn{from{opacity:0;transform:translateY(-10px)}to{opacity:1;transform:none}}
    `;
    document.head.appendChild(style);
  }

  window.showToast = window.showToast || function (message, type) {
    let stack = document.getElementById("auraGlobalToasts");
    if (!stack) {
      stack = document.createElement("div");
      stack.id = "auraGlobalToasts";
      stack.className = "aura-global-toasts";
      stack.setAttribute("aria-live", "polite");
      document.body.appendChild(stack);
    }
    const text = String(message || "Something went wrong.");
    const kind = type || (
      /error|failed|invalid|required|not found|could not|hindi|wala/i.test(text)
        ? "error"
        : /saved|updated|created|complete|success|subscribed|joined|learned/i.test(text)
          ? "success"
          : "info"
    );
    const toast = document.createElement("div");
    toast.className = "aura-global-toast " + kind;
    const copy = document.createElement("span");
    copy.textContent = text;
    const close = document.createElement("button");
    close.type = "button";
    close.textContent = "×";
    close.setAttribute("aria-label", "Close notification");
    const dismiss = function () {
      if (!toast.isConnected) return;
      toast.classList.add("leaving");
      setTimeout(function () { toast.remove(); }, 190);
    };
    close.addEventListener("click", dismiss);
    toast.append(copy, close);
    stack.appendChild(toast);
    while (stack.childElementCount > 4) stack.firstElementChild.remove();
    setTimeout(dismiss, kind === "error" ? 5200 : 3200);
  };

  window.auraPrompt = function (message, defaultValue, options) {
    options = options || {};
    return new Promise(function (resolve) {
      const overlay = document.createElement("div");
      overlay.className = "aura-global-prompt";
      const form = document.createElement("form");
      const title = document.createElement("h3");
      title.textContent = options.title || "MB Future Tech AI Chatbot";
      const copy = document.createElement("p");
      copy.textContent = message || "";
      const input = options.multiline
        ? document.createElement("textarea")
        : document.createElement("input");
      input.value = defaultValue || "";
      input.type = options.type || "text";
      const actions = document.createElement("div");
      actions.className = "aura-global-prompt-actions";
      const cancel = document.createElement("button");
      cancel.type = "button";
      cancel.textContent = "Cancel";
      const save = document.createElement("button");
      save.type = "submit";
      save.textContent = options.saveLabel || "Save";
      actions.append(cancel, save);
      form.append(title, copy, input, actions);
      overlay.appendChild(form);
      document.body.appendChild(overlay);
      const finish = function (value) {
        overlay.remove();
        resolve(value);
      };
      cancel.addEventListener("click", function () { finish(null); });
      overlay.addEventListener("click", function (event) {
        if (event.target === overlay) finish(null);
      });
      form.addEventListener("submit", function (event) {
        event.preventDefault();
        finish(input.value);
      });
      setTimeout(function () { input.focus(); input.select(); }, 0);
    });
  };
})();
