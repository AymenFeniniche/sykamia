document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("#chat-form");
  const input = document.querySelector("#user-input");
  const output = document.querySelector("#chat-output");
  if (!form || !input || !output) return;

  const API_BASE = "http://127.0.0.1:5500";
  const MODEL = "llama3.2";

  // ----------outils ----------
  const escapeHtml = (str = "") =>
    str
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");

  // format : soit texte normal, soit liste si le texte ressemble à une liste
  function formatAnswer(raw = "") {
    const safe = escapeHtml(raw).trim();
    if (!safe) return `<div>(pas de réponse)</div>`;

    const lines = safe.split("\n").map(l => l.trim()).filter(Boolean);
    const looksLikeList =
      lines.length >= 2 && lines.every(l => /^(\d+\.|\-|\*)\s+/.test(l));

    if (!looksLikeList) return `<div>${safe.replaceAll("\n", "<br>")}</div>`;

    const items = lines.map(l => l.replace(/^(\d+\.|\-|\*)\s+/, ""));
    return `<ul class="chat-list">${items.map(it => `<li>${it}</li>`).join("")}</ul>`;
  }

  function scrollBottom() {
    output.scrollTop = output.scrollHeight;
  }

  // ---------- UI messages ----------
  function addBubble(side, text, { isHtml = false } = {}) {
    const row = document.createElement("div");
    row.className = `chat-row ${side}`;

    const bubble = document.createElement("div");
    bubble.className = `chat-bubble ${side}`;

    bubble.innerHTML = isHtml ? text : formatAnswer(text);

    row.appendChild(bubble);
    output.appendChild(row);
    scrollBottom();
  }

  function addTyping() {
    if (document.querySelector("#typing-row")) return;

    const row = document.createElement("div");
    row.className = "chat-row left";
    row.id = "typing-row";

    const bubble = document.createElement("div");
    bubble.className = "chat-bubble left typing";
    bubble.innerHTML = `<div class="dots"><span></span><span></span><span></span></div>`;

    row.appendChild(bubble);
    output.appendChild(row);
    scrollBottom();
  }

  function removeTyping() {
    document.querySelector("#typing-row")?.remove();
  }

  function setLoading(loading) {
    input.disabled = loading;
    const btn = form.querySelector("button[type='submit']");
    if (btn) btn.disabled = loading;
  }

  // ---------- API ----------
  async function fetchBotAnswer(message) {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, model: MODEL }),
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data.answer || "";
  }

  // ---------- events ----------
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const msg = input.value.trim();
    if (!msg) return;

    // Message utilisateur (sans "Vous")
    addBubble("right", msg);
    input.value = "";

    setLoading(true);
    addTyping();

    try {
      const answer = await fetchBotAnswer(msg);
      removeTyping();

      // Réponse IA (sans "IA")
      addBubble("left", answer);
    } catch (err) {
      console.error(err);
      removeTyping();
      addBubble("left", "Erreur : impossible de contacter le serveur.");
    } finally {
      setLoading(false);
      input.focus();
    }
  });
});
