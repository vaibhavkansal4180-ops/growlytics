import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify
from backend.extensions import db
from backend.models import Sale, SaleItem, Product

sales_bp = Blueprint("sales", __name__, url_prefix="/api/sales")


def _generate_invoice_number() -> str:
    """Generate a clean, professional retail invoice number."""
    now = datetime.utcnow()
    # Count sales today to build sequential invoice
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    count_today = Sale.query.filter(Sale.created_at >= start_of_day).count()
    return f"INV-{now.strftime('%Y%m%d')}-{count_today + 1:04d}"


@sales_bp.route("", methods=["GET"])
def list_sales():
    """
    List sales transactions with customer, channel, and date sorting.
    """
    limit = int(request.args.get("limit", 20))
    offset = int(request.args.get("offset", 0))
    channel = request.args.get("channel")
    customer = request.args.get("customer")

    query = Sale.query

    if channel:
        query = query.filter(Sale.channel == channel)

    if customer:
        query = query.filter(Sale.customer_name.ilike(f"%{customer}%"))

    total_count = query.count()
    sales = query.order_by(Sale.created_at.desc()).offset(offset).limit(limit).all()

    return jsonify({
        "success": True,
        "total": total_count,
        "count": len(sales),
        "sales": [s.to_dict(include_items=True) for s in sales]
    })


@sales_bp.route("/<int:sale_id>", methods=["GET"])
def get_sale(sale_id):
    """Retrieve full sale detail and itemized invoice."""
    sale = Sale.query.get_or_404(sale_id)
    return jsonify({"success": True, "sale": sale.to_dict(include_items=True)})


@sales_bp.route("", methods=["POST"])
def record_sale():
    """
    Record a customer sale with atomic stock deduction and profit calculations.
    Uses database transaction rollback to guarantee consistency.
    """
    data = request.get_json() or {}

    customer_name = data.get("customer_name", "").strip() or "Walk-in Customer"
    channel = data.get("channel", "In-Store POS").strip()
    payment_method = data.get("payment_method", "Credit Card").strip()
    items_data = data.get("items", [])
    notes = data.get("notes", "").strip() or None

    try:
        discount = max(float(data.get("discount", 0.0)), 0.0)
        tax = max(float(data.get("tax", 0.0)), 0.0)
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Discount and tax must be valid numbers."}), 400

    if not items_data or not isinstance(items_data, list):
        return jsonify({"success": False, "error": "Sale must contain at least one item."}), 400

    # Start atomic database transaction
    try:
        subtotal = 0.0
        total_cost = 0.0
        sale_items = []

        # Validate all products and stock availability before mutating
        for idx, item_input in enumerate(items_data):
            product_id = item_input.get("product_id")
            if not product_id:
                return jsonify({"success": False, "error": f"Item #{idx+1} is missing product_id."}), 400

            try:
                qty = int(item_input.get("quantity", 1))
            except (ValueError, TypeError):
                return jsonify({"success": False, "error": f"Invalid quantity for item #{idx+1}."}), 400

            if qty <= 0:
                return jsonify({"success": False, "error": f"Quantity for item #{idx+1} must be at least 1."}), 400

            # Lock or fetch product
            product = Product.query.get(product_id)
            if not product:
                return jsonify({"success": False, "error": f"Product with ID {product_id} not found."}), 404

            # Verify stock sufficiency
            if product.stock_quantity < qty:
                return jsonify({
                    "success": False,
                    "error": f"Insufficient stock for '{product.name}'. Available: {product.stock_quantity}, Requested: {qty}."
                }), 400

            # Allow custom unit price override if provided, otherwise default to product selling price
            unit_price = float(item_input.get("unit_price", product.selling_price))
            unit_cost = float(product.cost_price)

            line_revenue = round(unit_price * qty, 2)
            line_cost = round(unit_cost * qty, 2)
            line_profit = round(line_revenue - line_cost, 2)

            subtotal += line_revenue
            total_cost += line_cost

            # Deduct inventory stock consistently
            product.stock_quantity -= qty

            sale_item = SaleItem(
                product_id=product.id,
                product_name=product.name,
                product_sku=product.sku,
                quantity=qty,
                unit_cost_price=unit_cost,
                unit_price=unit_price,
                line_revenue=line_revenue,
                line_profit=line_profit,
            )
            sale_items.append(sale_item)

        subtotal = round(subtotal, 2)
        total_cost = round(total_cost, 2)

        if discount > subtotal:
            discount = subtotal

        # Auto-compute 8% sales tax if not explicitly provided
        if "tax" in data and data["tax"] is not None:
            tax = max(float(data["tax"]), 0.0)
        else:
            tax = round((subtotal - discount) * 0.08, 2)

        total_revenue = round(subtotal - discount + tax, 2)
        # Net profit after discount
        estimated_profit = round(subtotal - discount - total_cost, 2)

        invoice_number = _generate_invoice_number()

        sale = Sale(
            invoice_number=invoice_number,
            customer_name=customer_name,
            channel=channel,
            payment_method=payment_method,
            subtotal=subtotal,
            discount=discount,
            tax=tax,
            total_revenue=total_revenue,
            total_cost=total_cost,
            estimated_profit=estimated_profit,
            notes=notes,
            created_at=datetime.utcnow(),
        )
        sale.items = sale_items

        db.session.add(sale)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Sale recorded successfully with invoice #{invoice_number}.",
            "sale": sale.to_dict(include_items=True)
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": f"Failed to record sale transaction: {str(e)}"
        }), 500
