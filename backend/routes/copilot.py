import json
import re
from datetime import datetime, timedelta
import urllib.request
import urllib.error
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import func, desc
from backend.extensions import db
from backend.models import Product, Sale, SaleItem, Category, CopilotInteraction

copilot_bp = Blueprint("copilot", __name__, url_prefix="/api/copilot")


def _gather_live_retail_context() -> dict:
    """Fetch live structured retail context directly from database."""
    total_revenue = db.session.query(func.coalesce(func.sum(Sale.total_revenue), 0.0)).scalar() or 0.0
    total_profit = db.session.query(func.coalesce(func.sum(Sale.estimated_profit), 0.0)).scalar() or 0.0
    total_orders = Sale.query.count()
    product_count = Product.query.count()

    # Low stock items
    low_stock_items = Product.query.filter(Product.stock_quantity <= Product.low_stock_threshold).all()

    # Top 5 products by quantity sold
    top_selling = (
        db.session.query(
            Product.name,
            Product.sku,
            func.coalesce(func.sum(SaleItem.quantity), 0).label("units_sold"),
            func.coalesce(func.sum(SaleItem.line_revenue), 0.0).label("revenue"),
            func.coalesce(func.sum(SaleItem.line_profit), 0.0).label("profit")
        )
        .join(SaleItem, Product.id == SaleItem.product_id)
        .group_by(Product.id)
        .order_by(desc("units_sold"))
        .limit(5)
        .all()
    )

    # Category performance
    categories = (
        db.session.query(
            Category.name,
            func.coalesce(func.sum(SaleItem.line_revenue), 0.0).label("revenue"),
            func.coalesce(func.sum(SaleItem.line_profit), 0.0).label("profit"),
            func.coalesce(func.sum(SaleItem.quantity), 0).label("units_sold")
        )
        .join(Product, Category.id == Product.category_id)
        .outerjoin(SaleItem, Product.id == SaleItem.product_id)
        .group_by(Category.id)
        .all()
    )

    return {
        "total_revenue": round(float(total_revenue), 2),
        "total_profit": round(float(total_profit), 2),
        "total_orders": int(total_orders),
        "product_count": int(product_count),
        "profit_margin_pct": round((total_profit / total_revenue * 100), 1) if total_revenue > 0 else 0.0,
        "low_stock_count": len(low_stock_items),
        "low_stock_items": [
            {
                "name": p.name,
                "sku": p.sku,
                "stock": p.stock_quantity,
                "threshold": p.low_stock_threshold,
                "reorder_needed": max(p.low_stock_threshold - p.stock_quantity + 10, 15)
            }
            for p in low_stock_items
        ],
        "top_selling": [
            {
                "name": t.name,
                "sku": t.sku,
                "units_sold": int(t.units_sold),
                "revenue": round(float(t.revenue), 2),
                "profit": round(float(t.profit), 2)
            }
            for t in top_selling
        ],
        "category_performance": [
            {
                "category": c.name,
                "revenue": round(float(c.revenue), 2),
                "profit": round(float(c.profit), 2),
                "units_sold": int(c.units_sold)
            }
            for c in categories
        ]
    }


def _run_rule_based_bi_engine(question: str, context: dict) -> dict:
    """
    Intelligent retail BI analytical fallback that answers questions
    using live database information with clear explanations and tables.
    """
    q = question.lower()

    # Intent 1: Best-selling / Top selling products
    if any(k in q for k in ["sell the most", "best selling", "top seller", "top product", "highest selling", "popular", "most sold"]):
        top = context["top_selling"]
        if not top:
            text = "No sales records are currently logged in the database to calculate top-selling products."
        else:
            text = "### 🏆 Best-Selling Products (Live Database Analysis)\n\n"
            text += "Based on actual recorded retail transactions, here are your top-performing products:\n\n"
            text += "| Rank | Product Name | SKU | Units Sold | Total Revenue | Net Profit |\n"
            text += "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
            for idx, p in enumerate(top, 1):
                text += f"| **#{idx}** | {p['name']} | `{p['sku']}` | **{p['units_sold']} units** | ${p['revenue']:,.2f} | ${p['profit']:,.2f} |\n"

            text += f"\n💡 **Strategic Growth Recommendation:** `{top[0]['name']}` is your leading volume driver with {top[0]['units_sold']} units sold. Ensure safety stock levels are increased to prevent stockouts during peak shopping periods."

        return {
            "intent": "top_selling_products",
            "response": text,
            "structured_data": {"top_products": top}
        }

    # Intent 2: Restocking / Low Stock
    if any(k in q for k in ["restock", "low stock", "out of stock", "reorder", "inventory alert", "stockout", "shortage"]):
        items = context["low_stock_items"]
        if not items:
            text = "### ✅ Inventory Health Status: Optimal\n\nAll products in your catalog are currently stocked above their minimum inventory safety threshold. No urgent purchase orders are required right now."
        else:
            text = f"### ⚠️ Low-Stock & Restocking Alerts ({len(items)} Items Require Action)\n\n"
            text += "The following items have dipped below their safety threshold and require immediate supplier PO generation:\n\n"
            text += "| Product Name | SKU | Current Stock | Safety Threshold | Suggested Reorder Qty |\n"
            text += "| :--- | :--- | :--- | :--- | :--- |\n"
            for item in items:
                text += f"| **{item['name']}** | `{item['sku']}` | 🔴 **{item['stock']}** | {item['threshold']} | **+{item['reorder_needed']} units** |\n"

            text += f"\n📦 **Action Item:** You can reorder these items directly via the **Inventory** panel using the 1-click 'Restock' button to replenish stock quantities."

        return {
            "intent": "restocking_alerts",
            "response": text,
            "structured_data": {"low_stock_items": items}
        }

    # Intent 3: Revenue / Profit / Financials
    if any(k in q for k in ["revenue", "profit", "margin", "financial", "earnings", "income", "sales total", "performance"]):
        tot_rev = context["total_revenue"]
        tot_prof = context["total_profit"]
        margin = context["profit_margin_pct"]
        orders = context["total_orders"]
        aov = round(tot_rev / orders, 2) if orders > 0 else 0.0

        text = "### 📊 Financial Performance & Profitability Overview\n\n"
        text += f"Live figures calculated across **{orders} completed customer orders**:\n\n"
        text += f"- **Gross Revenue:** ${tot_rev:,.2f}\n"
        text += f"- **Estimated Net Profit:** ${tot_prof:,.2f}\n"
        text += f"- **Blended Profit Margin:** **{margin}%**\n"
        text += f"- **Average Order Value (AOV):** ${aov:,.2f}\n\n"

        text += "#### Category Performance Breakdown:\n"
        text += "| Category | Revenue | Profit | Units Sold |\n"
        text += "| :--- | :--- | :--- | :--- |\n"
        for cat in context["category_performance"]:
            text += f"| **{cat['category']}** | ${cat['revenue']:,.2f} | ${cat['profit']:,.2f} | {cat['units_sold']} |\n"

        text += "\n💡 **Margin Insight:** Premium electronics and apparel categories contribute the highest dollar margins. Consider bundling specialty gourmet items with high-margin hardware to elevate average ticket size."

        return {
            "intent": "financial_summary",
            "response": text,
            "structured_data": context
        }

    # Intent 4: Categories / Product Mix
    if any(k in q for k in ["category", "categories", "department", "product mix", "catalog"]):
        cats = context["category_performance"]
        text = "### 🏷️ Department & Category Performance Breakdown\n\n"
        text += "Here is the performance distribution across your active product departments:\n\n"
        text += "| Department | Total Revenue | Net Profit | Margin % | Units Sold |\n"
        text += "| :--- | :--- | :--- | :--- | :--- |\n"
        for c in cats:
            c_margin = round((c['profit'] / c['revenue'] * 100), 1) if c['revenue'] > 0 else 0.0
            text += f"| **{c['category']}** | ${c['revenue']:,.2f} | ${c['profit']:,.2f} | **{c_margin}%** | {c['units_sold']} |\n"

        return {
            "intent": "category_breakdown",
            "response": text,
            "structured_data": {"categories": cats}
        }

    # Default Intent: Executive Briefing
    tot_rev = context["total_revenue"]
    tot_prof = context["total_profit"]
    orders = context["total_orders"]
    low_count = context["low_stock_count"]
    top_item = context["top_selling"][0]["name"] if context["top_selling"] else "None"

    text = f"### 💡 Growlytics Retail Intelligence Summary\n\n"
    text += f"Here is a real-time operational snapshot of your retail store:\n\n"
    text += f"- **Total Revenue:** ${tot_rev:,.2f} across **{orders} orders**.\n"
    text += f"- **Estimated Net Profit:** ${tot_prof:,.2f} (**{context['profit_margin_pct']}%** net margin).\n"
    text += f"- **Top-Selling Item:** **{top_item}**.\n"
    text += f"- **Inventory Risk:** **{low_count} items** currently at or below minimum threshold.\n\n"
    text += "You can ask me specific questions such as:\n"
    text += "- *Which products sell the most?*\n"
    text += "- *Which products need restocking immediately?*\n"
    text += "- *What was my revenue and profit margin by category?*\n"
    text += "- *Give me pricing recommendations to boost average order value.*"

    return {
        "intent": "general_briefing",
        "response": text,
        "structured_data": context
    }


@copilot_bp.route("/chat", methods=["POST"])
def chat():
    """
    Handle natural language retail intelligence queries.
    Seamlessly utilizes OpenAI/Gemini if configured, or the live database BI engine if offline.
    """
    data = request.get_json() or {}
    question = data.get("message", "").strip()

    if not question:
        return jsonify({"success": False, "error": "Question message cannot be empty."}), 400

    context = _gather_live_retail_context()

    openai_key = current_app.config.get("OPENAI_API_KEY")
    gemini_key = current_app.config.get("GEMINI_API_KEY")

    ai_model_name = "⚡ Growlytics Retail Intelligence Copilot (Database-Backed BI Engine)"
    response_text = ""
    structured_data = {}
    intent = "general_inquiry"

    # Option A: Gemini API if key is present
    if gemini_key:
        try:
            prompt = f"""You are Growlytics AI Copilot, an expert retail intelligence and store operations advisor.
Answer the store manager's question using this ACTUAL LIVE DATABASE METRICS snapshot:
{json.dumps(context, indent=2)}

Question: {question}

Provide an authoritative, data-driven answer with markdown formatting, tables where appropriate, and actionable merchandising advice. Reference specific figures and product names from the data."""

            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            payload_bytes = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
            req = urllib.request.Request(url, data=payload_bytes, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status == 200:
                    res_json = json.loads(resp.read().decode("utf-8"))
                    response_text = res_json["candidates"][0]["content"]["parts"][0]["text"]
                    ai_model_name = "Google Gemini 1.5 Flash (Live Context Injected)"
                    intent = "llm_gemini_analysis"
        except Exception as e:
            current_app.logger.warning(f"Gemini API invocation fallback: {e}")

    # Option B: OpenAI API if configured and Gemini was not used
    if not response_text and openai_key:
        try:
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": f"You are Growlytics AI Copilot. Analyze the store manager's question using the live store database snapshot:\n{json.dumps(context, indent=2)}"
                    },
                    {"role": "user", "content": question}
                ],
                "temperature": 0.3
            }
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {openai_key}",
                    "Content-Type": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status == 200:
                    res_json = json.loads(resp.read().decode("utf-8"))
                    response_text = res_json["choices"][0]["message"]["content"]
                    ai_model_name = "OpenAI GPT-4o-mini (Live Context Injected)"
                    intent = "llm_openai_analysis"
        except Exception as e:
            current_app.logger.warning(f"OpenAI API invocation fallback: {e}")

    # Option C: High-Precision Live Database BI Engine Fallback (Offline Mode)
    if not response_text:
        engine_result = _run_rule_based_bi_engine(question, context)
        response_text = engine_result["response"]
        structured_data = engine_result.get("structured_data", {})
        intent = engine_result.get("intent", "rule_based_bi")

    # Persist interaction safely in database
    try:
        interaction = CopilotInteraction(
            question=question,
            intent=intent,
            response_text=response_text,
            insights_json=json.dumps(structured_data) if structured_data else None,
            model_used=ai_model_name
        )
        db.session.add(interaction)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.warning(f"Failed to record copilot interaction: {e}")

    return jsonify({
        "success": True,
        "question": question,
        "response": response_text,
        "model": ai_model_name,
        "is_ai_fallback": "LLM" not in ai_model_name,
        "timestamp": datetime.utcnow().isoformat()
    })


@copilot_bp.route("/history", methods=["GET"])
def get_history():
    """Retrieve past questions asked to Copilot."""
    interactions = CopilotInteraction.query.order_by(CopilotInteraction.created_at.desc()).limit(10).all()
    return jsonify({
        "success": True,
        "history": [i.to_dict() for i in interactions]
    })
