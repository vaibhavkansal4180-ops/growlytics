from flask import Blueprint, request, jsonify
from backend.extensions import db
from backend.models import Product, Category, SaleItem
from backend.routes.auth import login_required

inventory_bp = Blueprint("inventory", __name__, url_prefix="/api/inventory")


@inventory_bp.route("/products", methods=["GET"])
def list_products():
    """
    List products with search query, category filtering, and stock status filters.
    """
    search = request.args.get("search", "").strip()
    category_id = request.args.get("category_id")
    stock_status = request.args.get("status")  # 'low', 'out', 'in_stock'

    query = Product.query

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Product.name.ilike(search_filter)) |
            (Product.sku.ilike(search_filter)) |
            (Product.barcode.ilike(search_filter))
        )

    if category_id and category_id.isdigit():
        query = query.filter(Product.category_id == int(category_id))

    if stock_status == "low":
        query = query.filter(Product.stock_quantity <= Product.low_stock_threshold, Product.stock_quantity > 0)
    elif stock_status == "out":
        query = query.filter(Product.stock_quantity == 0)
    elif stock_status == "in_stock":
        query = query.filter(Product.stock_quantity > Product.low_stock_threshold)

    products = query.order_by(Product.name.asc()).all()

    return jsonify({
        "success": True,
        "count": len(products),
        "products": [p.to_dict() for p in products]
    })


@inventory_bp.route("/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    """Retrieve single product details."""
    product = Product.query.get_or_404(product_id)
    return jsonify({"success": True, "product": product.to_dict()})


@inventory_bp.route("/products", methods=["POST"])
def add_product():
    """
    Create a new product with strict validation and duplicate-SKU prevention.
    """
    data = request.get_json() or {}

    name = data.get("name", "").strip()
    sku = data.get("sku", "").strip().upper()
    category_id = data.get("category_id")

    # Validation
    if not name:
        return jsonify({"success": False, "error": "Product name is required."}), 400

    if not sku:
        return jsonify({"success": False, "error": "Product SKU is required."}), 400

    if not category_id:
        return jsonify({"success": False, "error": "Product category is required."}), 400

    try:
        cost_price = float(data.get("cost_price", 0.0))
        selling_price = float(data.get("selling_price", 0.0))
        stock_quantity = int(data.get("stock_quantity", 0))
        low_stock_threshold = int(data.get("low_stock_threshold", 10))
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Prices and quantities must be valid positive numbers."}), 400

    if cost_price < 0 or selling_price < 0 or stock_quantity < 0 or low_stock_threshold < 0:
        return jsonify({"success": False, "error": "Prices and stock quantities cannot be negative."}), 400

    # Ensure category exists
    category = Category.query.get(category_id)
    if not category:
        return jsonify({"success": False, "error": f"Category ID {category_id} does not exist."}), 400

    # Check for duplicate SKU
    existing = Product.query.filter_by(sku=sku).first()
    if existing:
        return jsonify({
            "success": False,
            "error": f"A product with SKU '{sku}' already exists: '{existing.name}'."
        }), 409

    product = Product(
        name=name,
        sku=sku,
        category_id=category.id,
        cost_price=cost_price,
        selling_price=selling_price,
        stock_quantity=stock_quantity,
        low_stock_threshold=low_stock_threshold,
        barcode=data.get("barcode", "").strip() or None,
        description=data.get("description", "").strip() or None
    )

    db.session.add(product)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Product '{name}' added successfully.",
        "product": product.to_dict()
    }), 201


@inventory_bp.route("/products/<int:product_id>", methods=["PUT", "PATCH"])
def update_product(product_id):
    """
    Update existing product with validation and duplicate SKU prevention.
    """
    product = Product.query.get_or_404(product_id)
    data = request.get_json() or {}

    if "name" in data:
        name = data["name"].strip()
        if not name:
            return jsonify({"success": False, "error": "Product name cannot be empty."}), 400
        product.name = name

    if "sku" in data:
        sku = data["sku"].strip().upper()
        if not sku:
            return jsonify({"success": False, "error": "SKU cannot be empty."}), 400
        # Check if SKU changed and conflicts with another product
        existing = Product.query.filter(Product.sku == sku, Product.id != product.id).first()
        if existing:
            return jsonify({"success": False, "error": f"SKU '{sku}' is already assigned to '{existing.name}'."}), 409
        product.sku = sku

    if "category_id" in data:
        cat = Category.query.get(data["category_id"])
        if not cat:
            return jsonify({"success": False, "error": "Selected category does not exist."}), 400
        product.category_id = cat.id

    if "cost_price" in data:
        try:
            val = float(data["cost_price"])
            if val < 0:
                raise ValueError
            product.cost_price = val
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "Cost price must be a non-negative number."}), 400

    if "selling_price" in data:
        try:
            val = float(data["selling_price"])
            if val < 0:
                raise ValueError
            product.selling_price = val
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "Selling price must be a non-negative number."}), 400

    if "stock_quantity" in data:
        try:
            val = int(data["stock_quantity"])
            if val < 0:
                raise ValueError
            product.stock_quantity = val
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "Stock quantity must be a non-negative integer."}), 400

    if "low_stock_threshold" in data:
        try:
            val = int(data["low_stock_threshold"])
            if val < 0:
                raise ValueError
            product.low_stock_threshold = val
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "Low stock threshold must be a non-negative integer."}), 400

    if "barcode" in data:
        product.barcode = data["barcode"].strip() or None

    if "description" in data:
        product.description = data["description"].strip() or None

    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Product '{product.name}' updated successfully.",
        "product": product.to_dict()
    })


@inventory_bp.route("/products/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    """
    Safely delete a product. If it has historical sale items, disallow hard delete or handle safely.
    """
    product = Product.query.get_or_404(product_id)

    # Check if item is linked to past sales
    past_sales_count = SaleItem.query.filter_by(product_id=product.id).count()
    if past_sales_count > 0:
        return jsonify({
            "success": False,
            "error": f"Cannot delete '{product.name}' because it has {past_sales_count} historical sales records. You may set its stock quantity to 0 instead."
        }), 400

    prod_name = product.name
    db.session.delete(product)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Product '{prod_name}' deleted successfully."
    })


@inventory_bp.route("/categories", methods=["GET"])
def list_categories():
    """List all categories with product counts."""
    categories = Category.query.order_by(Category.name.asc()).all()
    return jsonify({
        "success": True,
        "categories": [c.to_dict() for c in categories]
    })


@inventory_bp.route("/adjust-stock", methods=["POST"])
def adjust_stock():
    """
    Quick adjustment of stock (e.g., from low stock alert reorder action).
    """
    data = request.get_json() or {}
    product_id = data.get("product_id")
    quantity_to_add = data.get("quantity")

    if not product_id or quantity_to_add is None:
        return jsonify({"success": False, "error": "product_id and quantity are required."}), 400

    try:
        qty = int(quantity_to_add)
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Quantity must be an integer."}), 400

    product = Product.query.get_or_404(product_id)
    if product.stock_quantity + qty < 0:
        return jsonify({
            "success": False,
            "error": f"Cannot reduce stock below 0. Current stock is {product.stock_quantity}."
        }), 400

    product.stock_quantity += qty
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Stock for '{product.name}' adjusted by {qty:+d}. New stock: {product.stock_quantity}.",
        "product": product.to_dict()
    })
