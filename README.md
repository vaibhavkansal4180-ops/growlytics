# 🚀 Growlytics — AI-Powered Retail Intelligence Platform
> **Turn Insights Into Growth**

Growlytics is an enterprise-grade retail intelligence platform designed for multi-category retail operators. It tracks inventory velocity, safeguards stock thresholds, records atomic transactions with automated margin and profit calculations, and features an **AI Business Copilot** capable of answering complex commercial questions using live database telemetry.

---

## 📸 Key Features

### 1. 📊 Executive Dashboard
- **Live Financial KPIs:** Database-backed Real-time Gross Revenue, Estimated Net Profit, Total Orders, and Monitored SKUs.
- **Velocity Charts:** Dual-series interactive Chart.js line visualizations tracking daily revenue and profit trajectories.
- **Department Mix:** Doughnut breakdown of revenue contribution by category.
- **Top Velocity Drivers:** Real-time ranking of best-selling products by volume, dollar yield, and margin.
- **Recent Transaction Stream:** Live order feed with verified settlement status.
- **Low-Stock Alert Bar:** Dynamic threshold detection alerting operations to impending stockouts.

### 2. 📦 Inventory Intelligence
- **Full Catalog CRUD:** Add, inspect, update, and safely delete products.
- **SKU Uniqueness & Validation:** Server-side duplicate prevention and data integrity enforcement.
- **Live Filter Engine:** Instant multi-category filtering, text search across SKU / Name / Barcode, and stock condition toggles (In Stock, Low Stock, Out of Stock).
- **1-Click Quick Restock:** Rapid batch replenishment directly from the table.

### 3. 💳 Sales & Transaction Ledger
- **Atomic Stock Deduction:** Transactions execute inside database transactions (`try ... except ... rollback`) guaranteeing zero orphaned stock deductions.
- **Financial Calculation Engine:** Automated line-item revenue, product cost attribution, sales tax (8%), promotional discount deductions, and calculated net margin.
- **Itemized Invoices:** Interactive receipt modal rendering full item breakdowns, price snapshots, and verified invoice numbers.

### 4. 🤖 AI Business Copilot
- **Live Database Context Injection:** Queries live SQLite / PostgreSQL tables to extract active revenue, margins, bestsellers, and stock deficits.
- **Hybrid AI Engine:**
  - **Online Mode:** Seamlessly connects to **Google Gemini** or **OpenAI GPT-4o-mini** if API keys are configured on the server.
  - **Offline Mode:** Built-in rule-based analytical Business Intelligence engine providing formatted tables and actionable merchandising recommendations without requiring external cloud LLM dependencies.
- **Security & Privacy:** Server-side API key containment. No keys are ever exposed in frontend JavaScript.

### 5. 🔐 Security & Access Control
- Secure password hashing using Werkzeug `generate_password_hash` / `check_password_hash`.
- Session-based authentication with `HttpOnly` and `SameSite` cookie protections.
- Demo evaluation credentials pre-configured with 1-click autofill for instant prototype auditing.

---

## 🛠️ Tech Stack

- **Frontend:** Vanilla HTML5, CSS3 Custom Properties Design System, Modern Vanilla JavaScript (ES6+).
- **Backend:** Python 3.13, Flask 3.1.
- **ORM & Database:** SQLAlchemy 2.0, Flask-SQLAlchemy 3.1, PostgreSQL (production) with transparent SQLite fallback (development).
- **Data Visualizations:** Chart.js 4.4 via CDN.
- **Cloud Hosting:** Vercel Serverless (`@vercel/python`).

---

## 📂 Architecture

```
growlytics/
├── api/
│   └── index.py            # Vercel serverless entry point
├── backend/
│   ├── app.py              # Application factory & route registration
│   ├── config.py           # Database URL parser (Postgres/Neon/SQLite)
│   ├── extensions.py       # SQLAlchemy & CORS instances
│   ├── models.py           # User, Product, Category, Sale, SaleItem, Copilot
│   ├── seed.py             # Realistic 30-day retail dataset
│   └── routes/
│       ├── auth.py         # Login, register, logout, session management
│       ├── dashboard.py    # KPIs, trends, bestsellers, low-stock alerts
│       ├── inventory.py    # Products CRUD, search, stock adjustment
│       ├── sales.py        # Atomic sales checkout, stock deduction, receipts
│       └── copilot.py      # AI Copilot engine (Gemini/OpenAI/Offline BI)
├── frontend/
│   ├── index.html          # Executive Dashboard
│   ├── inventory.html      # Inventory Management
│   ├── sales.html          # Sales & Transactions
│   ├── copilot.html        # AI Business Copilot
│   ├── login.html          # Authentication & Demo login
│   ├── css/
│   │   └── style.css       # Custom design system
│   └── js/
│       ├── api.js          # Unified HTTP client & notifications
│       ├── dashboard.js    # Dashboard metrics & Chart.js controllers
│       ├── inventory.js    # Product modal handlers & search
│       ├── sales.js        # Dynamic multi-item checkout & invoice viewer
│       └── copilot.js      # Chat engine & prompt suggestions
├── tests/
│   └── test_api.py         # 10 comprehensive unit & integration tests
├── .env.example            # Environment variables template
├── .gitignore              # Sensitive file & database exclusions
├── Procfile                # Production process declaration
├── requirements.txt        # Python dependency manifest
├── run.py                  # Local development server runner
└── vercel.json             # Vercel deployment & routing configuration
```

---

## ⚙️ Environment Variables

Create a `.env` file in the project root:

```ini
# Flask Environment
FLASK_ENV=production
FLASK_DEBUG=0
PORT=5000
SECRET_KEY=your-secure-random-64-char-secret-key

# PostgreSQL Database (Neon, Supabase, Vercel Postgres, AWS RDS)
DATABASE_URL=postgresql://user:password@host:5432/growlytics?sslmode=require

# CORS Configuration
CORS_ORIGINS=*

# Optional AI LLM Keys (If omitted, offline BI engine activates)
OPENAI_API_KEY=
GEMINI_API_KEY=
```

---

## 🚀 Running Locally

1. **Clone the repository:**
   ```bash
   git clone https://github.com/vaibhavkansal4180-ops/growlytics.git
   cd growlytics
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the application:**
   ```bash
   python run.py
   ```
   Open `http://localhost:5000` in your browser.

4. **Run the Automated Test Suite:**
   ```bash
   python -m unittest discover -s tests -v
   ```

---

## 👥 Demo Credentials

- **Email:** `admin@growlytics.io`
- **Password:** `growlytics2026`
- **Role:** Chief Retail Operations Officer
