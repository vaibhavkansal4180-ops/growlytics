/**
 * GROWLYTICS — API Client & Core Utilities
 */

const API = {
  async get(endpoint) {
    try {
      const res = await fetch(endpoint, {
        headers: { "Accept": "application/json" }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || `HTTP error ${res.status}`);
      return data;
    } catch (err) {
      console.error(`API GET error on ${endpoint}:`, err);
      throw err;
    }
  },

  async post(endpoint, body) {
    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json"
        },
        body: JSON.stringify(body)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || `HTTP error ${res.status}`);
      return data;
    } catch (err) {
      console.error(`API POST error on ${endpoint}:`, err);
      throw err;
    }
  },

  async put(endpoint, body) {
    try {
      const res = await fetch(endpoint, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json"
        },
        body: JSON.stringify(body)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || `HTTP error ${res.status}`);
      return data;
    } catch (err) {
      console.error(`API PUT error on ${endpoint}:`, err);
      throw err;
    }
  },

  async delete(endpoint) {
    try {
      const res = await fetch(endpoint, {
        method: "DELETE",
        headers: { "Accept": "application/json" }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || `HTTP error ${res.status}`);
      return data;
    } catch (err) {
      console.error(`API DELETE error on ${endpoint}:`, err);
      throw err;
    }
  }
};

// UI Formatting Utilities
function formatCurrency(amount) {
  const num = parseFloat(amount || 0);
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2
  }).format(num);
}

function formatNumber(num) {
  return new Intl.NumberFormat("en-US").format(num || 0);
}

function formatDate(isoString) {
  if (!isoString) return "-";
  const date = new Date(isoString);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
}

// Toast Notifications
function showToast(message, type = "success") {
  let container = document.querySelector(".toast-container");
  if (!container) {
    container = document.createElement("div");
    container.className = "toast-container";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span>${type === "success" ? "✓" : "⚠️"}</span>
    <div>${message}</div>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Check System Health & Update Badge
async function checkSystemHealth() {
  try {
    const res = await API.get("/api/health");
    const badge = document.getElementById("db-health-badge");
    if (badge && res.status === "healthy") {
      badge.innerHTML = `<span class="status-dot"></span> Live DB (${res.database.type})`;
    }
  } catch (e) {
    const badge = document.getElementById("db-health-badge");
    if (badge) {
      badge.innerHTML = `<span class="status-dot" style="background:#ef4444"></span> DB Reconnecting`;
    }
  }
}

// Load Current User in Sidebar
async function loadCurrentUser() {
  try {
    const res = await API.get("/api/auth/me");
    const nameEl = document.getElementById("user-name-display");
    const roleEl = document.getElementById("user-role-display");
    const avatarEl = document.getElementById("user-avatar-display");

    if (res.authenticated && res.user) {
      if (nameEl) nameEl.textContent = res.user.name;
      if (roleEl) roleEl.textContent = res.user.role;
      if (avatarEl) {
        avatarEl.textContent = res.user.name.split(" ").map(w => w[0]).join("").toUpperCase().slice(0, 2);
      }
    } else {
      if (nameEl) nameEl.textContent = "Alexander Vance";
      if (roleEl) roleEl.textContent = "Chief Retail Operations";
      if (avatarEl) avatarEl.textContent = "AV";
    }
  } catch (err) {
    console.warn("User state check fallback");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  checkSystemHealth();
  loadCurrentUser();
});
