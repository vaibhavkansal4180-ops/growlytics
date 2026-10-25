from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from backend.extensions import db


class User(db.Model):
    """User account model for secure authentication."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), default="Store Manager", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Category(db.Model):
    """Retail product category model."""
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    products = db.relationship("Product", back_populates="category", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description or "",
            "product_count": self.products.count() if hasattr(self.products, "count") else len(self.products),
        }


class Product(db.Model):
    """Inventory item model with stock tracking and pricing intelligence."""
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    sku = db.Column(db.String(50), unique=True, nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    category = db.relationship("Category", back_populates="products")

    cost_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    stock_quantity = db.Column(db.Integer, default=0, nullable=False)
    low_stock_threshold = db.Column(db.Integer, default=10, nullable=False)
    barcode = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    sale_items = db.relationship("SaleItem", back_populates="product", lazy="dynamic")

    @property
    def is_low_stock(self) -> bool:
        return self.stock_quantity <= self.low_stock_threshold

    @property
    def unit_profit(self) -> float:
        return round(self.selling_price - self.cost_price, 2)

    @property
    def margin_percentage(self) -> float:
        if self.selling_price > 0:
            return round(((self.selling_price - self.cost_price) / self.selling_price) * 100, 1)
        return 0.0

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "sku": self.sku,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else "Uncategorized",
            "cost_price": round(float(self.cost_price), 2),
            "selling_price": round(float(self.selling_price), 2),
            "stock_quantity": int(self.stock_quantity),
            "low_stock_threshold": int(self.low_stock_threshold),
            "is_low_stock": bool(self.is_low_stock),
            "unit_profit": float(self.unit_profit),
            "margin_percentage": float(self.margin_percentage),
            "barcode": self.barcode or "",
            "description": self.description or "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Sale(db.Model):
    """Customer retail transaction order model."""
    __tablename__ = "sales"

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    customer_name = db.Column(db.String(120), default="Walk-in Customer", nullable=False)
    channel = db.Column(db.String(50), default="In-Store POS", nullable=False)
    payment_method = db.Column(db.String(50), default="Credit Card", nullable=False)

    subtotal = db.Column(db.Float, nullable=False)
    discount = db.Column(db.Float, default=0.0, nullable=False)
    tax = db.Column(db.Float, default=0.0, nullable=False)
    total_revenue = db.Column(db.Float, nullable=False)
    total_cost = db.Column(db.Float, nullable=False)
    estimated_profit = db.Column(db.Float, nullable=False)
    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True, nullable=False)
    items = db.relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan", lazy="joined")

    def to_dict(self, include_items: bool = True):
        data = {
            "id": self.id,
            "invoice_number": self.invoice_number,
            "customer_name": self.customer_name,
            "channel": self.channel,
            "payment_method": self.payment_method,
            "subtotal": round(float(self.subtotal), 2),
            "discount": round(float(self.discount), 2),
            "tax": round(float(self.tax), 2),
            "total_revenue": round(float(self.total_revenue), 2),
            "total_cost": round(float(self.total_cost), 2),
            "estimated_profit": round(float(self.estimated_profit), 2),
            "profit_margin": round((self.estimated_profit / self.total_revenue * 100), 1) if self.total_revenue > 0 else 0.0,
            "notes": self.notes or "",
            "item_count": sum(item.quantity for item in self.items),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_items:
            data["items"] = [item.to_dict() for item in self.items]
        return data


class SaleItem(db.Model):
    """Line item within a sale transaction."""
    __tablename__ = "sale_items"

    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("sales.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)

    sale = db.relationship("Sale", back_populates="items")
    product = db.relationship("Product", back_populates="sale_items")

    product_name = db.Column(db.String(150), nullable=False)
    product_sku = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_cost_price = db.Column(db.Float, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    line_revenue = db.Column(db.Float, nullable=False)
    line_profit = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "product_sku": self.product_sku,
            "quantity": int(self.quantity),
            "unit_cost_price": round(float(self.unit_cost_price), 2),
            "unit_price": round(float(self.unit_price), 2),
            "line_revenue": round(float(self.line_revenue), 2),
            "line_profit": round(float(self.line_profit), 2),
        }


class CopilotInteraction(db.Model):
    """Historical questions and answers generated by AI Business Copilot."""
    __tablename__ = "copilot_interactions"

    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    intent = db.Column(db.String(100), nullable=True)
    response_text = db.Column(db.Text, nullable=False)
    insights_json = db.Column(db.Text, nullable=True)
    model_used = db.Column(db.String(80), default="Rule-Based Retail BI Engine", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "question": self.question,
            "intent": self.intent,
            "response_text": self.response_text,
            "insights_json": self.insights_json,
            "model_used": self.model_used,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
