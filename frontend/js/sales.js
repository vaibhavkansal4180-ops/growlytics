/**
 * GROWLYTICS — Sales & Transactions Controller
 */

let availableProducts = [];
let salesSearchTimer = null;

async function loadProductsForSale() {
  try {
    const res = await API.get("/api/inventory/products");
    if (res.success) {
      availableProducts = res.products;
    }
  } catch (err) {
    console.error("Error loading products for sales:", err);
  }
}

async function loadSales() {
  const search = document.getElementById("sales-search-input").value.trim();
  const channel = document.getElementById("channel-filter-select").value;

  let url = "/api/sales?limit=50&";
  if (search) url += `customer=${encodeURIComponent(search)}&`;
  if (channel) url += `channel=${encodeURIComponent(channel)}&`;

  const tbody = document.getElementById("sales-table-body");
  try {
    const res = await API.get(url);
    if (!res.success) throw new Error(res.error);

    document.getElementById("sales-count-display").textContent = res.total;

    if (!res.sales.length) {
      tbody.innerHTML = `<tr><td colspan="10" style="text-align:center; padding: 40px; color:var(--text-muted);">
        No transaction records found matching the filter criteria.
      </td></tr>`;
      return;
    }

    tbody.innerHTML = res.sales.map(s => `
      <tr>
        <td>
          <a href="javascript:void(0)" onclick="viewInvoice(${s.id})" style="font-weight:700; color:#0b132b; text-decoration:none;">
            ${s.invoice_number}
          </a>
        </td>
        <td style="font-size:12px; color:var(--text-muted);">${formatDate(s.created_at)}</td>
        <td><strong>${s.customer_name}</strong></td>
        <td><span class="badge-tag badge-channel">${s.channel}</span></td>
        <td>${s.payment_method}</td>
        <td>${s.item_count} items</td>
        <td><strong>${formatCurrency(s.total_revenue)}</strong></td>
        <td><span style="font-weight:700; color:#047857;">${formatCurrency(s.estimated_profit)}</span></td>
        <td><span class="kpi-badge positive">${s.profit_margin}%</span></td>
        <td style="text-align: right;">
          <button class="btn btn-secondary btn-sm" onclick="viewInvoice(${s.id})">
            View Receipt
          </button>
        </td>
      </tr>
    `).join("");

  } catch (err) {
    console.error("Error loading sales:", err);
    tbody.innerHTML = `<tr><td colspan="10" style="text-align:center; color:var(--danger); padding:20px;">
      Error loading sales ledger: ${err.message}
    </td></tr>`;
  }
}

function handleSalesSearch() {
  clearTimeout(salesSearchTimer);
  salesSearchTimer = setTimeout(() => {
    loadSales();
  }, 300);
}

// Sale Line Items Management
function addItemRow() {
  const container = document.getElementById("sale-items-container");
  const rowIndex = container.children.length;

  const row = document.createElement("div");
  row.className = "sale-item-row";
  row.style = "display: flex; gap: 10px; align-items: flex-end; background: #ffffff; padding: 10px; border-radius: var(--radius-md); border: 1px solid var(--card-border);";

  const optionsHtml = availableProducts.map(p =>
    `<option value="${p.id}" data-price="${p.selling_price}" data-cost="${p.cost_price}" data-stock="${p.stock_quantity}">
      ${p.name} ($${p.selling_price.toFixed(2)}) — [${p.stock_quantity} in stock]
    </option>`
  ).join("");

  row.innerHTML = `
    <div style="flex: 2;">
      <label class="form-label" style="font-size: 11px;">Select Product</label>
      <select class="form-select item-prod-select" style="width: 100%; height: 38px;" onchange="handleProductSelected(this)" required>
        <option value="">Select item...</option>
        ${optionsHtml}
      </select>
    </div>
    <div style="width: 80px;">
      <label class="form-label" style="font-size: 11px;">Qty</label>
      <input type="number" min="1" class="form-input item-qty-input" value="1" style="height: 38px;" oninput="recalculateSaleTotals()" required>
    </div>
    <div style="width: 100px;">
      <label class="form-label" style="font-size: 11px;">Price ($)</label>
      <input type="number" step="0.01" class="form-input item-price-input" style="height: 38px;" oninput="recalculateSaleTotals()" required>
    </div>
    <div style="width: 90px; text-align: right; padding-bottom: 8px;">
      <div style="font-size: 10px; color: var(--text-muted);">Line Total</div>
      <strong class="item-line-total" style="font-size: 13px;">$0.00</strong>
    </div>
    <button type="button" class="btn btn-danger btn-sm" onclick="removeItemRow(this)" style="height: 38px; margin-bottom: 1px;" title="Remove">✕</button>
  `;

  container.appendChild(row);

  // Auto-select first product if available
  const select = row.querySelector(".item-prod-select");
  if (availableProducts.length > 0) {
    select.value = availableProducts[0].id;
    handleProductSelected(select);
  }
}

function handleProductSelected(selectEl) {
  const row = selectEl.closest(".sale-item-row");
  const selectedOption = selectEl.selectedOptions[0];
  const price = selectedOption.getAttribute("data-price") || 0;
  row.querySelector(".item-price-input").value = parseFloat(price).toFixed(2);
  recalculateSaleTotals();
}

function removeItemRow(btn) {
  const container = document.getElementById("sale-items-container");
  if (container.children.length <= 1) {
    showToast("A sale must contain at least one item", "error");
    return;
  }
  btn.closest(".sale-item-row").remove();
  recalculateSaleTotals();
}

function recalculateSaleTotals() {
  const rows = document.querySelectorAll(".sale-item-row");
  let subtotal = 0;
  let totalCost = 0;

  rows.forEach(row => {
    const select = row.querySelector(".item-prod-select");
    const qtyInput = row.querySelector(".item-qty-input");
    const priceInput = row.querySelector(".item-price-input");
    const lineTotalEl = row.querySelector(".item-line-total");

    const qty = parseInt(qtyInput.value) || 0;
    const price = parseFloat(priceInput.value) || 0;
    const selectedOption = select.selectedOptions[0];
    const cost = selectedOption ? (parseFloat(selectedOption.getAttribute("data-cost")) || 0) : 0;

    const lineTotal = qty * price;
    subtotal += lineTotal;
    totalCost += qty * cost;

    lineTotalEl.textContent = formatCurrency(lineTotal);
  });

  const discount = Math.min(parseFloat(document.getElementById("sale-discount").value) || 0, subtotal);
  const tax = (subtotal - discount) * 0.08;
  const netTotal = subtotal - discount + tax;
  const profit = subtotal - discount - totalCost;
  const marginPct = netTotal > 0 ? ((profit / netTotal) * 100).toFixed(1) : 0;

  document.getElementById("calc-subtotal").textContent = formatCurrency(subtotal);
  document.getElementById("calc-discount").textContent = `-${formatCurrency(discount)}`;
  document.getElementById("calc-tax").textContent = `+${formatCurrency(tax)}`;
  document.getElementById("calc-total").textContent = formatCurrency(netTotal);
  document.getElementById("calc-profit").textContent = `+${formatCurrency(profit)} (${marginPct}% margin)`;
}

// Modal Handlers
function openNewSaleModal() {
  document.getElementById("sale-form").reset();
  const container = document.getElementById("sale-items-container");
  container.innerHTML = "";
  addItemRow();
  document.getElementById("sale-modal").classList.add("active");
}

function closeNewSaleModal() {
  document.getElementById("sale-modal").classList.remove("active");
}

async function handleSaleSubmit(e) {
  e.preventDefault();
  const rows = document.querySelectorAll(".sale-item-row");
  const items = [];

  for (const row of rows) {
    const prodId = parseInt(row.querySelector(".item-prod-select").value);
    const qty = parseInt(row.querySelector(".item-qty-input").value);
    const price = parseFloat(row.querySelector(".item-price-input").value);

    if (!prodId || !qty || qty <= 0) {
      showToast("Please ensure all line items have valid products and quantities", "error");
      return;
    }

    items.push({
      product_id: prodId,
      quantity: qty,
      unit_price: price
    });
  }

  const payload = {
    customer_name: document.getElementById("sale-customer").value.trim(),
    channel: document.getElementById("sale-channel").value,
    payment_method: document.getElementById("sale-payment").value,
    discount: parseFloat(document.getElementById("sale-discount").value) || 0,
    tax: 0, // Handled automatically by server
    items: items
  };

  try {
    const res = await API.post("/api/sales", payload);
    showToast(res.message, "success");
    closeNewSaleModal();
    await loadProductsForSale(); // Refresh stock counts
    loadSales();
    viewInvoice(res.sale.id); // Open receipt
  } catch (err) {
    showToast(err.message, "error");
  }
}

// View Invoice
async function viewInvoice(saleId) {
  try {
    const res = await API.get(`/api/sales/${saleId}`);
    if (!res.success) throw new Error(res.error);

    const s = res.sale;
    document.getElementById("invoice-modal-title").textContent = `Receipt — ${s.invoice_number}`;

    const itemsHtml = s.items.map(i => `
      <tr>
        <td>
          <div style="font-weight:600;">${i.product_name}</div>
          <div style="font-size:11px; color:#64748b; font-family:monospace;">${i.product_sku}</div>
        </td>
        <td style="text-align:center;">${i.quantity}</td>
        <td style="text-align:right;">${formatCurrency(i.unit_price)}</td>
        <td style="text-align:right; font-weight:700;">${formatCurrency(i.line_revenue)}</td>
      </tr>
    `).join("");

    document.getElementById("invoice-modal-content").innerHTML = `
      <div style="border-bottom: 2px solid #0b132b; padding-bottom: 14px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: flex-start;">
        <div>
          <div style="font-size: 20px; font-weight: 800; color: #0b132b;">GROWLYTICS RETAIL</div>
          <div style="font-size: 11px; color: #64748b;">AI-Powered Retail Intelligence Platform</div>
        </div>
        <div style="text-align: right;">
          <div style="font-weight: 800; font-size: 15px; color: #b45309;">${s.invoice_number}</div>
          <div style="font-size: 12px; color: #64748b;">${formatDate(s.created_at)}</div>
        </div>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px; font-size: 12.5px;">
        <div>
          <span style="color:#64748b;">Customer:</span> <strong>${s.customer_name}</strong><br>
          <span style="color:#64748b;">Channel:</span> ${s.channel}
        </div>
        <div>
          <span style="color:#64748b;">Payment Method:</span> <strong>${s.payment_method}</strong><br>
          <span style="color:#64748b;">Status:</span> <span class="badge-tag badge-in-stock">Paid & Verified</span>
        </div>
      </div>

      <table class="grow-table" style="margin-bottom: 16px;">
        <thead>
          <tr>
            <th>Item Description</th>
            <th style="text-align:center;">Qty</th>
            <th style="text-align:right;">Unit Price</th>
            <th style="text-align:right;">Total</th>
          </tr>
        </thead>
        <tbody>
          ${itemsHtml}
        </tbody>
      </table>

      <div style="background: #faf9f6; border-radius: var(--radius-md); padding: 14px; border: 1px solid var(--card-border);">
        <div style="display:flex; justify-content:space-between; margin-bottom:4px; font-size:12.5px;">
          <span>Subtotal:</span> <strong>${formatCurrency(s.subtotal)}</strong>
        </div>
        ${s.discount > 0 ? `
          <div style="display:flex; justify-content:space-between; margin-bottom:4px; font-size:12.5px; color:#dc2626;">
            <span>Discount Applied:</span> <strong>-${formatCurrency(s.discount)}</strong>
          </div>
        ` : ""}
        <div style="display:flex; justify-content:space-between; margin-bottom:8px; font-size:12.5px;">
          <span>Sales Tax:</span> <strong>+${formatCurrency(s.tax)}</strong>
        </div>
        <div style="display:flex; justify-content:space-between; font-size:16px; font-weight:800; border-top:1px solid #e2e8f0; padding-top:8px;">
          <span>Grand Total:</span> <span style="color:#b45309;">${formatCurrency(s.total_revenue)}</span>
        </div>
        <div style="display:flex; justify-content:space-between; font-size:12px; font-weight:600; color:#047857; margin-top:6px;">
          <span>Calculated Net Margin:</span> <span>${formatCurrency(s.estimated_profit)} (${s.profit_margin}%)</span>
        </div>
      </div>
    `;

    document.getElementById("invoice-modal").classList.add("active");
  } catch (err) {
    showToast(err.message, "error");
  }
}

function closeInvoiceModal() {
  document.getElementById("invoice-modal").classList.remove("active");
}

document.addEventListener("DOMContentLoaded", async () => {
  await loadProductsForSale();
  loadSales();

  // Check URL params to auto-open sale modal
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get("action") === "new") {
    openNewSaleModal();
  }
  if (urlParams.get("invoice")) {
    document.getElementById("sales-search-input").value = urlParams.get("invoice");
    loadSales();
  }
});
