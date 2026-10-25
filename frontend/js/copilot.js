/**
 * GROWLYTICS — AI Business Copilot Controller
 */

function appendUserMessage(text) {
  const container = document.getElementById("chat-messages-wrap");
  const bubble = document.createElement("div");
  bubble.className = "chat-bubble user";
  bubble.textContent = text;
  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

function appendThinkingBubble() {
  const container = document.getElementById("chat-messages-wrap");
  const bubble = document.createElement("div");
  bubble.className = "chat-bubble bot thinking-bubble";
  bubble.id = "copilot-thinking-indicator";
  bubble.innerHTML = `
    <div style="display:flex; align-items:center; gap:8px; color:var(--text-muted); font-size:13px;">
      <span class="status-dot" style="background:#f59e0b;"></span>
      <span>Querying live database and analyzing retail intelligence...</span>
    </div>
  `;
  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

function removeThinkingBubble() {
  const el = document.getElementById("copilot-thinking-indicator");
  if (el) el.remove();
}

function appendBotMessage(markdownText, modelName, isFallback) {
  removeThinkingBubble();
  const container = document.getElementById("chat-messages-wrap");
  const bubble = document.createElement("div");
  bubble.className = "chat-bubble bot";

  // Parse markdown if library loaded, else raw text
  let renderedHtml = markdownText;
  if (window.marked && typeof window.marked.parse === "function") {
    renderedHtml = window.marked.parse(markdownText);
  }

  bubble.innerHTML = `
    <div style="font-size:11px; color:#64748b; font-weight:600; margin-bottom:8px; display:flex; justify-content:space-between; border-bottom:1px solid #f1f0ec; padding-bottom:4px;">
      <span>${modelName || "Growlytics Retail Intelligence"}</span>
      <span>${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
    </div>
    <div class="chat-markdown-body">${renderedHtml}</div>
  `;

  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

async function askCopilot(question) {
  const input = document.getElementById("chat-input");
  input.value = question;
  document.getElementById("btn-send-chat").click();
}

async function handleChatSubmit(e) {
  e.preventDefault();
  const input = document.getElementById("chat-input");
  const question = input.value.trim();
  if (!question) return;

  appendUserMessage(question);
  input.value = "";
  appendThinkingBubble();

  try {
    const res = await API.post("/api/copilot/chat", { message: question });
    if (!res.success) throw new Error(res.error || "Failed to generate copilot response");

    // Update active engine badge
    const badge = document.getElementById("active-engine-badge");
    if (badge && res.model) {
      badge.textContent = res.model;
      if (res.is_ai_fallback) {
        badge.style.backgroundColor = "#fef3c7";
        badge.style.color = "#92400e";
      } else {
        badge.style.backgroundColor = "#ecfdf5";
        badge.style.color = "#065f46";
      }
    }

    appendBotMessage(res.response, res.model, res.is_ai_fallback);
  } catch (err) {
    removeThinkingBubble();
    appendBotMessage(`⚠️ **Analysis Error:** ${err.message}. Please check your database connection.`, "Error", true);
  }
}

function clearChat() {
  const container = document.getElementById("chat-messages-wrap");
  container.innerHTML = `
    <div class="chat-bubble bot">
      <h3 style="font-size: 15px; font-weight: 700; color: #0b132b; margin-bottom: 6px;">
        👋 Welcome to Growlytics AI Business Copilot
      </h3>
      <p style="margin-bottom: 8px;">
        Chat history cleared. What questions can I answer about your retail inventory, revenue, or margins?
      </p>
    </div>
  `;
}
