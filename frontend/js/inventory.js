/**
 * GROWLYTICS — Inventory Controller
 */

let allCategories = [];
let searchDebounceTimer = null;

async function loadCategories() {
  try {
    const res = await API.get("/api/inventory/categories");
    if (res.success) {
      allCategories = res.categories;

      // Populate filter dropdown
      const filterSelect = document.getElementById("category-filter-select");
      filterSelect.innerHTML = `<option value="">All Categories</option>` +
        allCategories.map(c => `<option value="${c.id}">${c.name} (${c.product_count})</option>`).join("");

      // Populate form dropdown
      const formSelect = document.getElementById("form-category");
      formSelect.innerHTML = `<option value="">Select a Category...</option>` +
        allCategories.map(c => `<option value="${c.id}">${c.name}</option>`).join("");
    }
  } catch (err) {
    console.error("Error loading categories:", err);
  }
}

async function loadInventory() {
  const search = document.getElementById("inventory-search-input").value.trim();
  const catId = document.getElementById("category-filter-select").value;
  const status = document.getElementById("status-filter-select").value;

  let url = `/api/inventory/products?`;
  if (search) url += `search=${encodeURIComponent(search)}&`;
  if (catId) url += `category_id=${catId}&`;
  if (status) url += `status=${status}&`;

  const tbody = document.getElementById("inventory-table-body");
  try {
    const res = await API.get(url);
    if (!res.success) throw new Error(res.error);

    document.getElementById("product-count-display").textContent = res.count;

    if (!res.products.length) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding: 40px; color:var(--text-muted);">
        No products match the selected criteria.
      </td></tr>`;
      return;
    }

    tbody.innerHTML = res.products.map(p => {
      let statusBadge = `<span class="badge-tag badge-in-stock">In Stock</span>`;
      if (p.stock_quantity === 0) {
        statusBadge = `<span class="badge-tag badge-out-of-stock">Out of Stock</span>`;
      } else if (p.is_low_stock) {
        statusBadge = `<span class="badge-tag badge-low-stock">⚠️ Low Stock (${p.stock_quantity})</span>`;
      }

      return `
        <tr>
          <td>
            <div class="product-cell">
              <span class="product-name-txt">${p.name}</span>
              <span class="product-sku-txt">${p.sku}</span>
            </div>
          </td>
          <td><span class="badge-tag badge-category">${p.category_name}</span></td>
          <td>${formatCurrency(p.cost_price)}</td>
          <td><strong>${formatCurrency(p.selling_price)}</strong></td>
          <td>
            <span style="font-weight:700; color:${p.margin_percentage >= 30 ? '#047857' : '#b45309'};">
              ${p.margin_percentage}%
            </span>
          </td>
          <td><strong>${p.stock_quantity}</strong> units</td>
          <td style="color:var(--text-muted);">${p.low_stock_threshold} min</td>
          <td>${statusBadge}</td>
          <td style="text-align: right;">
            <div style="display:inline-flex; gap:6px;">
              <button class="btn btn-secondary btn-sm" onclick='openRestockModal(${JSON.stringify(p)})' title="Quick Restock">
                + Restock
              </button>
              <button class="btn btn-secondary btn-sm" onclick='openEditProductModal(${JSON.stringify(p)})' title="Edit">
                Edit
              </button>
              <button class="btn btn-danger btn-sm" onclick="handleDeleteProduct(${p.id}, '${p.name.replace(/'/g, "\\'")}')" title="Delete">
                Delete
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join("");

  } catch (err) {
    console.error("Error loading inventory:", err);
    tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; color:var(--danger); padding:20px;">
      Error loading inventory: ${err.message}
    </td></tr>`;
  }
}

function handleSearchInput() {
  clearTimeout(searchDebounceTimer);
  searchDebounceTimer = setTimeout(() => {
    loadInventory();
  }, 300);
}

// Add/Edit Product Modal
function openAddProductModal() {
  document.getElementById("modal-product-title").textContent = "Add New Inventory Item";
  document.getElementById("form-product-id").value = "";
  document.getElementById("product-form").reset();
  updateMarginPreview();
  document.getElementById("product-modal").classList.add("active");
}

function openEditProductModal(product) {
  document.getElementById("modal-product-title").textContent = `Edit Product: ${product.name}`;
  document.getElementById("form-product-id").value = product.id;
  document.getElementById("form-name").value = product.name;
  document.getElementById("form-sku").value = product.sku;
  document.getElementById("form-category").value = product.category_id;
  document.getElementById("form-cost-price").value = product.cost_price;
  document.getElementById("form-selling-price").value = product.selling_price;
  document.getElementById("form-stock").value = product.stock_quantity;
  document.getElementById("form-threshold").value = product.low_stock_threshold;
  document.getElementById("form-barcode").value = product.barcode || "";
  document.getElementById("form-description").value = product.description || "";
  updateMarginPreview();
  document.getElementById("product-modal").classList.add("active");
}

function closeProductModal() {
  document.getElementById("product-modal").classList.remove("active");
}

function updateMarginPreview() {
  const cost = parseFloat(document.getElementById("form-cost-price").value) || 0;
  const sell = parseFloat(document.getElementById("form-selling-price").value) || 0;
  const profit = sell - cost;
  const marginPct = sell > 0 ? ((profit / sell) * 100).toFixed(1) : 0;
  const el = document.getElementById("form-margin-preview");
  if (profit >= 0) {
    el.style.color = "var(--success)";
    el.textContent = `+$${profit.toFixed(2)} profit per unit (${marginPct}% margin)`;
  } else {
    el.style.color = "var(--danger)";
    el.textContent = `-$${Math.abs(profit).toFixed(2)} negative margin (${marginPct}%)`;
  }
}

async function handleProductSubmit(e) {
  e.preventDefault();
  const id = document.getElementById("form-product-id").value;
  const payload = {
    name: document.getElementById("form-name").value.trim(),
    sku: document.getElementById("form-sku").value.trim().toUpperCase(),
    category_id: parseInt(document.getElementById("form-category").value),
    cost_price: parseFloat(document.getElementById("form-cost-price").value),
    selling_price: parseFloat(document.getElementById("form-selling-price").value),
    stock_quantity: parseInt(document.getElementById("form-stock").value),
    low_stock_threshold: parseInt(document.getElementById("form-threshold").value),
    barcode: document.getElementById("form-barcode").value.trim(),
    description: document.getElementById("form-description").value.trim()
  };

  try {
    let res;
    if (id) {
      res = await API.put(`/api/inventory/products/${id}`, payload);
      showToast(`Updated '${payload.name}' successfully!`, "success");
    } else {
      res = await API.post(`/api/inventory/products`, payload);
      showToast(`Added '${payload.name}' to catalog!`, "success");
    }
    closeProductModal();
    loadInventory();
  } catch (err) {
    showToast(err.message || "Failed to save product", "error");
  }
}

async function handleDeleteProduct(id, name) {
  if (!confirm(`Are you sure you want to permanently delete '${name}'? This cannot be undone.`)) {
    return;
  }
  try {
    const res = await API.delete(`/api/inventory/products/${id}`);
    showToast(res.message || "Product deleted.", "success");
    loadInventory();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// Quick Restock Modal
function openRestockModal(product) {
  document.getElementById("restock-product-id").value = product.id;
  document.getElementById("restock-product-label").innerHTML =
    `Restocking: <strong>${product.name}</strong><br>Current stock: <strong>${product.stock_quantity}</strong> (Threshold: ${product.low_stock_threshold})`;
  document.getElementById("restock-quantity-input").value = Math.max(product.low_stock_threshold - product.stock_quantity + 15, 20);
  document.getElementById("restock-modal").classList.add("active");
}

function closeRestockModal() {
  document.getElementById("restock-modal").classList.remove("active");
}

async function submitRestock() {
  const id = document.getElementById("restock-product-id").value;
  const qty = parseInt(document.getElementById("restock-quantity-input").value);
  if (!qty || qty <= 0) {
    showToast("Please enter a valid positive quantity", "error");
    return;
  }

  try {
    const res = await API.post("/api/inventory/adjust-stock", {
      product_id: id,
      quantity: qty
    });
    showToast(res.message, "success");
    closeRestockModal();
    loadInventory();
  } catch (err) {
    showToast(err.message, "error");
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  await loadCategories();

  // Check URL params for direct filter link
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get("filter") === "low") {
    document.getElementById("status-filter-select").value = "low";
  }

  loadInventory();
});
