import unittest
import json
import sys
import os
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import create_app
from backend.config import TestingConfig
from backend.extensions import db
from backend.models import User, Category, Product, Sale, SaleItem
from backend.seed import seed_database


class GrowlyticsAPITestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_health_check(self):
        """Test system health and database diagnostic endpoint."""
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["database"]["connected"])

    def test_auth_login_success(self):
        """Test admin login with seeded demo credentials."""
        payload = {
            "email": "admin@growlytics.io",
            "password": "growlytics2026"
        }
        res = self.client.post("/api/auth/login", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["user"]["email"], "admin@growlytics.io")

    def test_auth_login_invalid(self):
        """Test authentication rejection with invalid credentials."""
        payload = {"email": "admin@growlytics.io", "password": "wrongpassword"}
        res = self.client.post("/api/auth/login", json=payload)
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertFalse(data["success"])

    def test_dashboard_stats(self):
        """Test dashboard statistics calculation."""
        res = self.client.get("/api/dashboard/stats?period=30d")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        m = data["metrics"]
        self.assertGreater(m["total_revenue"], 0)
        self.assertGreater(m["estimated_profit"], 0)
        self.assertGreater(m["total_orders"], 0)
        self.assertGreater(m["product_count"], 0)

    def test_inventory_list(self):
        """Test product listing and category filtering."""
        res = self.client.get("/api/inventory/products")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertGreater(len(data["products"]), 0)

    def test_inventory_add_and_duplicate_sku(self):
        """Test adding new product and enforcing SKU uniqueness."""
        category = Category.query.first()
        payload = {
            "name": "Test Mechanical Keyboard",
            "sku": "TEST-KEY-99",
            "category_id": category.id,
            "cost_price": 45.0,
            "selling_price": 120.0,
            "stock_quantity": 30,
            "low_stock_threshold": 10
        }
        # First creation succeeds
        res = self.client.post("/api/inventory/products", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["product"]["sku"], "TEST-KEY-99")

        # Duplicate SKU rejection
        res_dup = self.client.post("/api/inventory/products", json=payload)
        self.assertEqual(res_dup.status_code, 409)
        data_dup = res_dup.get_json()
        self.assertFalse(data_dup["success"])

    def test_inventory_stock_adjustment(self):
        """Test quick stock adjustment."""
        product = Product.query.first()
        initial_stock = product.stock_quantity
        payload = {
            "product_id": product.id,
            "quantity": 15
        }
        res = self.client.post("/api/inventory/adjust-stock", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["product"]["stock_quantity"], initial_stock + 15)

    def test_record_sale_and_inventory_deduction(self):
        """Test transaction recording with atomic inventory deduction and profit calculation."""
        product = Product.query.filter(Product.stock_quantity > 10).first()
        prod_id = product.id
        initial_stock = product.stock_quantity
        unit_cost = product.cost_price
        unit_sell = product.selling_price
        qty_to_buy = 2

        payload = {
            "customer_name": "Test Customer",
            "channel": "In-Store POS",
            "payment_method": "Credit Card",
            "discount": 10.0,
            "items": [
                {
                    "product_id": prod_id,
                    "quantity": qty_to_buy,
                    "unit_price": unit_sell
                }
            ]
        }

        res = self.client.post("/api/sales", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data["success"])
        sale = data["sale"]

        # Check math
        expected_subtotal = round(unit_sell * qty_to_buy, 2)
        expected_cost = round(unit_cost * qty_to_buy, 2)
        expected_tax = round((expected_subtotal - 10.0) * 0.08, 2)
        expected_revenue = round(expected_subtotal - 10.0 + expected_tax, 2)
        expected_profit = round(expected_subtotal - 10.0 - expected_cost, 2)

        self.assertEqual(sale["subtotal"], expected_subtotal)
        self.assertEqual(sale["total_revenue"], expected_revenue)
        self.assertEqual(sale["estimated_profit"], expected_profit)

        # Check that product inventory stock was deducted consistently
        refreshed_prod = Product.query.get(prod_id)
        self.assertEqual(refreshed_prod.stock_quantity, initial_stock - qty_to_buy)

    def test_record_sale_insufficient_stock_rollback(self):
        """Test that sale transaction is safely rejected if stock is insufficient."""
        product = Product.query.first()
        initial_stock = product.stock_quantity

        payload = {
            "customer_name": "Greedy Buyer",
            "items": [
                {
                    "product_id": product.id,
                    "quantity": initial_stock + 500,  # Far more than available
                    "unit_price": product.selling_price
                }
            ]
        }

        res = self.client.post("/api/sales", json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Insufficient stock", data["error"])

        # Verify stock was untouched
        refreshed_prod = Product.query.get(product.id)
        self.assertEqual(refreshed_prod.stock_quantity, initial_stock)

    def test_copilot_chat_bi_fallback(self):
        """Test AI Copilot natural language questions against live database."""
        # Query 1: Top sellers
        res1 = self.client.post("/api/copilot/chat", json={"message": "Which products sell the most?"})
        self.assertEqual(res1.status_code, 200)
        data1 = res1.get_json()
        self.assertTrue(data1["success"])
        self.assertIn("Best-Selling Products", data1["response"])

        # Query 2: Restocking
        res2 = self.client.post("/api/copilot/chat", json={"message": "Which products need restocking?"})
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        self.assertTrue(data2["success"])
        self.assertIn("Restocking Alerts", data2["response"])

        # Query 3: Financials
        res3 = self.client.post("/api/copilot/chat", json={"message": "What is my total revenue and profit margin?"})
        self.assertEqual(res3.status_code, 200)
        data3 = res3.get_json()
        self.assertTrue(data3["success"])
        self.assertIn("Gross Revenue", data3["response"])


if __name__ == "__main__":
    unittest.main()
