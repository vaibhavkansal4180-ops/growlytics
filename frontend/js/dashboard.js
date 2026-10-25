/**
 * GROWLYTICS — Dashboard Controller
 */

let salesChart = null;
let categoryChart = null;
let currentPeriod = "30d";

async function loadDashboardStats(period = "30d") {
  try {
    const res = await API.get(`/api/dashboard/stats?period=${period}`);
    if (res.success) {
      const m = res.metrics;
      document.getElementById("kpi-revenue").textContent = formatCurrency(m.total_revenue);
      document.getElementById("kpi-profit").textContent = formatCurrency(m.estimated_profit);
      document.getElementById("kpi-orders").textContent = formatNumber(m.total_orders);
      document.getElementById("kpi-products").textContent = formatNumber(m.product_count);

      document.getElementById("kpi-margin-badge").textContent = `${m.profit_margin_percent}% Margin`;
      document.getElementById("kpi-aov-badge").textContent = `${formatCurrency(m.average_order_value)} AOV`;

      const growthBadge = document.getElementById("kpi-growth-badge");
      if (m.revenue_growth_percent >= 0) {
        growthBadge.className = "kpi-badge positive";
        growthBadge.textContent = `↑ ${m.revenue_growth_percent}%`;
      } else {
        growthBadge.className = "kpi-badge negative";
        growthBadge.textContent = `↓ ${Math.abs(m.revenue_growth_percent)}%`;
      }

      const lowBadge = document.getElementById("kpi-low-stock-badge");
      lowBadge.textContent = `${m.low_stock_count} Low Stock`;
      lowBadge.className = m.low_stock_count > 0 ? "kpi-badge negative" : "kpi-badge positive";

      // Sidebar low stock badge
      const sbBadge = document.getElementById("sidebar-low-badge");
      if (sbBadge) {
        if (m.low_stock_count > 0) {
          sbBadge.style.display = "inline-block";
          sbBadge.textContent = m.low_stock_count;
        } else {
          sbBadge.style.display = "none";
        }
      }
    }
  } catch (err) {
    console.error("Error loading dashboard stats:", err);
  }
}

async function loadSalesTrendChart(period = "30d") {
  try {
    const res = await API.get(`/api/dashboard/sales-trend?period=${period}`);
    if (!res.success) return;

    const ctx = document.getElementById("salesTrendChart").getContext("2d");

    if (salesChart) {
      salesChart.destroy();
    }

    salesChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: res.labels,
        datasets: [
          {
            label: "Revenue ($)",
            data: res.datasets.revenue,
            borderColor: "#f59e0b",
            backgroundColor: "rgba(245, 158, 11, 0.08)",
            borderWidth: 2.5,
            fill: true,
            tension: 0.35,
            pointRadius: res.labels.length > 20 ? 1 : 3,
            pointHoverRadius: 6,
          },
          {
            label: "Net Profit ($)",
            data: res.datasets.profit,
            borderColor: "#10b981",
            backgroundColor: "rgba(16, 185, 129, 0.04)",
            borderWidth: 2.5,
            fill: true,
            tension: 0.35,
            pointRadius: res.labels.length > 20 ? 1 : 3,
            pointHoverRadius: 6,
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: {
            position: "top",
            labels: {
              boxWidth: 12,
              font: { size: 12, weight: "bold" },
              color: "#475569"
            }
          },
          tooltip: {
            callbacks: {
              label: (context) => ` ${context.dataset.label}: ${formatCurrency(context.raw)}`
            }
          }
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { font: { size: 11 }, color: "#64748b", maxTicksLimit: 12 }
          },
          y: {
            grid: { color: "#f1f0ec" },
            ticks: {
              font: { size: 11 },
              color: "#64748b",
              callback: (val) => `$${val}`
            }
          }
        }
      }
    });
  } catch (err) {
    console.error("Error loading sales trend chart:", err);
  }
}

async function loadCategoryChart() {
  try {
    const res = await API.get("/api/dashboard/category-breakdown");
    if (!res.success || !res.categories.length) return;

    const ctx = document.getElementById("categoryChart").getContext("2d");
    const labels = res.categories.map(c => c.category);
    const data = res.categories.map(c => c.revenue);

    const colors = [
      "#f59e0b", "#3b82f6", "#10b981", "#8b5cf6", "#ec4899", "#14b8a6"
    ];

    if (categoryChart) categoryChart.destroy();

    categoryChart = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: labels,
        datasets: [{
          data: data,
          backgroundColor: colors.slice(0, labels.length),
          borderWidth: 2,
          borderColor: "#ffffff"
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "right",
            labels: { boxWidth: 10, font: { size: 11 }, color: "#475569" }
          },
          tooltip: {
            callbacks: {
              label: (c) => ` ${c.label}: ${formatCurrency(c.raw)}`
            }
          }
        },
        cutout: "68%"
      }
    });
  } catch (err) {
    console.error("Error loading category chart:", err);
  }
}

async function loadTopProducts() {
  try {
    const res = await API.get("/api/dashboard/top-products?limit=5");
    const tbody = document.getElementById("top-products-tbody");
    if (!res.success || !res.top_products.length) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 20px;">No product sales recorded yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = res.top_products.map(p => `
      <tr>
        <td>
          <div class="product-cell">
            <span class="product-name-txt">#${p.rank} ${p.name}</span>
            <span class="product-sku-txt">${p.sku}</span>
          </div>
        </td>
        <td><span class="badge-tag badge-category">${p.category}</span></td>
        <td><strong>${formatNumber(p.units_sold)}</strong> units</td>
        <td>${formatCurrency(p.total_revenue)}</td>
        <td><strong style="color: #047857;">${p.margin_percentage}%</strong></td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Error loading top products:", err);
  }
}

async function loadRecentTransactions() {
  try {
    const res = await API.get("/api/dashboard/recent-transactions?limit=5");
    const tbody = document.getElementById("recent-sales-tbody");
    if (!res.success || !res.transactions.length) {
      tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding: 20px;">No transactions recorded yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = res.transactions.map(t => `
      <tr>
        <td>
          <a href="/sales?invoice=${t.invoice_number}" style="font-weight:700; color:#0b132b; text-decoration:none;">
            ${t.invoice_number}
          </a>
          <div style="font-size:11px; color:#64748b;">${formatDate(t.created_at)}</div>
        </td>
        <td>${t.customer_name}</td>
        <td><strong>${formatCurrency(t.total_revenue)}</strong></td>
        <td><span class="badge-tag badge-channel">${t.channel}</span></td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Error loading recent transactions:", err);
  }
}

async function loadLowStockAlerts() {
  try {
    const res = await API.get("/api/dashboard/low-stock-alerts");
    const banner = document.getElementById("low-stock-banner");
    if (res.success && res.count > 0) {
      banner.style.display = "flex";
      document.getElementById("low-stock-banner-title").textContent =
        `Urgent Restocking Alert: ${res.count} Products Below Safety Threshold`;
      document.getElementById("low-stock-banner-desc").textContent =
        `Items such as ${res.alerts.slice(0, 2).map(a => a.name).join(", ")} require immediate supplier reordering to avoid stockouts.`;
    } else {
      banner.style.display = "none";
    }
  } catch (err) {
    console.error("Error checking low stock:", err);
  }
}

function changePeriod(period, btn) {
  document.querySelectorAll(".date-pill").forEach(el => el.classList.remove("active"));
  btn.classList.add("active");
  currentPeriod = period;
  loadDashboardStats(period);
  loadSalesTrendChart(period);
}

function toggleDataset(index) {
  if (!salesChart) return;
  const isVisible = salesChart.isDatasetVisible(index);
  salesChart.setDatasetVisibility(index, !isVisible);
  salesChart.update();
}

document.addEventListener("DOMContentLoaded", () => {
  loadDashboardStats(currentPeriod);
  loadSalesTrendChart(currentPeriod);
  loadCategoryChart();
  loadTopProducts();
  loadRecentTransactions();
  loadLowStockAlerts();
});
