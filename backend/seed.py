import random
from datetime import datetime, timedelta
from backend.extensions import db
from backend.models import User, Category, Product, Sale, SaleItem


def seed_database(force: bool = False):
    """
    Safely seed initial retail dataset if database is empty.
    Never automatically deletes or overwrites existing user data.
    """
    if not force and Product.query.first() is not None:
        return {"status": "skipped", "message": "Database already contains product data."}

    # 1. Create Default Administrative User
    if not User.query.filter_by(email="admin@growlytics.io").first():
        admin = User(
            name="Alexander Vance",
            email="admin@growlytics.io",
            role="Chief Retail Operations Officer",
        )
        admin.set_password("growlytics2026")
        db.session.add(admin)

    # 2. Categories
    category_data = [
        {"name": "Electronics & Audio", "description": "High-margin smart devices, premium headphones, and tech accessories"},
        {"name": "Apparel & Footwear", "description": "Curated fashion, activewear, and everyday essentials"},
        {"name": "Home & Kitchen", "description": "Artisan cookware, modern appliances, and home decor"},
        {"name": "Health & Beauty", "description": "Organic skincare, wellness supplements, and luxury grooming"},
        {"name": "Specialty Gourmet", "description": "Artisanal coffee beans, gourmet snacks, and organic teas"},
    ]

    categories = {}
    for c_info in category_data:
        cat = Category.query.filter_by(name=c_info["name"]).first()
        if not cat:
            cat = Category(name=c_info["name"], description=c_info["description"])
            db.session.add(cat)
            db.session.flush()
        categories[c_info["name"]] = cat

    # 3. Products (including high-sellers, healthy stock, and low-stock items)
    products_spec = [
        # Electronics
        ("Aura ANC Pro Wireless Headphones", "ELEC-AUR-01", "Electronics & Audio", 95.00, 249.99, 42, 15, "88091234001"),
        ("HyperBeam 4K Ultra Laser Projector", "ELEC-HYP-02", "Electronics & Audio", 380.00, 799.00, 14, 8, "88091234002"),
        ("PulseFit Smartwatch Horizon Edition", "ELEC-PUL-03", "Electronics & Audio", 65.00, 179.50, 6, 12, "88091234003"), # Low stock!
        ("VoltStream GaN 100W Fast Charger", "ELEC-VOL-04", "Electronics & Audio", 16.50, 48.00, 85, 20, "88091234004"),
        ("EchoSphere Studio Hi-Fi Speaker", "ELEC-ECH-05", "Electronics & Audio", 110.00, 289.00, 8, 10, "88091234005"), # Low stock!

        # Apparel
        ("Merino Wool Everyday Crew Sweater", "APP-MER-11", "Apparel & Footwear", 38.00, 115.00, 56, 15, "88091234011"),
        ("AeroFlex Technical Running Jacket", "APP-AER-12", "Apparel & Footwear", 42.00, 135.00, 28, 12, "88091234012"),
        ("TerraForm Water-Resistant Chelsea Boots", "APP-TER-13", "Apparel & Footwear", 68.00, 185.00, 4, 10, "88091234013"), # Low stock!
        ("EcoLoom Organic Cotton Chino Pants", "APP-ECO-14", "Apparel & Footwear", 24.00, 78.00, 64, 15, "88091234014"),
        ("Stratus Waterproof Commuter Backpack", "APP-STR-15", "Apparel & Footwear", 35.00, 98.00, 31, 10, "88091234015"),

        # Home & Kitchen
        ("Artisan Cast Iron Dutch Oven 6-Qt", "HOME-DUT-21", "Home & Kitchen", 52.00, 159.00, 19, 10, "88091234021"),
        ("Precision Burr Conical Coffee Grinder", "HOME-BUR-22", "Home & Kitchen", 75.00, 189.99, 7, 10, "88091234022"), # Low stock!
        ("Nordic Minimalist Stoneware Dinner Set", "HOME-NOR-23", "Home & Kitchen", 45.00, 129.50, 35, 12, "88091234023"),
        ("PureMist Ultrasonic Aroma Diffuser", "HOME-PUR-24", "Home & Kitchen", 18.00, 54.00, 48, 15, "88091234024"),
        ("ChefElite Damascus Steel Santoku Knife", "HOME-CHE-25", "Home & Kitchen", 32.00, 89.99, 5, 8, "88091234025"), # Low stock!

        # Health & Beauty
        ("Botanical Hydra-Glow Facial Serum", "BEA-BOT-31", "Health & Beauty", 14.00, 58.00, 72, 20, "88091234031"),
        ("SilkNourish Peptide Night Cream", "BEA-SIL-32", "Health & Beauty", 19.50, 65.00, 50, 15, "88091234032"),
        ("Zenith Clean Whey Protein Isolate (2lb)", "BEA-ZEN-33", "Health & Beauty", 22.00, 59.99, 9, 15, "88091234033"), # Low stock!
        ("Aromatherapy Mineral Bath Soak (Bath)", "BEA-ARO-34", "Health & Beauty", 9.00, 28.00, 60, 12, "88091234034"),

        # Gourmet
        ("Single-Origin Ethiopian Yirgacheffe (12oz)", "GOUR-ETH-41", "Specialty Gourmet", 7.50, 22.50, 80, 25, "88091234041"),
        ("Raw Wildflower Honeycomb Jar (500g)", "GOUR-HON-42", "Specialty Gourmet", 6.80, 18.99, 11, 15, "88091234042"), # Low stock!
        ("Matcha Ceremonial Grade Green Tea (50g)", "GOUR-MAT-43", "Specialty Gourmet", 12.00, 34.00, 44, 15, "88091234043"),
    ]

    created_products = []
    for name, sku, cat_name, cost, sell, stock, low, bcode in products_spec:
        p = Product.query.filter_by(sku=sku).first()
        if not p:
            p = Product(
                name=name,
                sku=sku,
                category_id=categories[cat_name].id,
                cost_price=cost,
                selling_price=sell,
                stock_quantity=stock,
                low_stock_threshold=low,
                barcode=bcode,
                description=f"Premium commercial grade {name.lower()} engineered for retail excellence."
            )
            db.session.add(p)
            db.session.flush()
        created_products.append(p)

    # 4. Realistic Historical Sales Transactions (Last 30 Days)
    now = datetime.utcnow()
    customers = [
        "Liam Gallagher", "Sophia Chen", "Marcus Sterling", "Elena Rostova",
        "David Kim", "Amara Okafor", "Benjamin Hayes", "Chloe Dubois",
        "Mateo Hernandez", "Priya Sharma", "Oliver Wright", "Zara Lindqvist"
    ]
    channels = ["In-Store POS", "In-Store POS", "Online Store", "In-Store POS", "B2B Wholesale"]
    pay_methods = ["Credit Card", "Apple Pay / Contactless", "Credit Card", "Debit Card", "UPI / Digital Wallet", "Cash"]

    existing_sales = Sale.query.count()
    if not force and existing_sales > 0:
        return {"status": "skipped", "message": "Database already contains sales data."}

    random.seed(42)  # Deterministic seed for reproducible realistic curves
    inv_counter = 1000 + existing_sales

    # Generate 55 transactions spread across the past 30 days
    for day_offset in range(30, -1, -1):
        day_date = now - timedelta(days=day_offset)
        # More sales on weekends (Friday=4, Saturday=5, Sunday=6)
        num_sales_today = random.choice([2, 3, 4]) if day_date.weekday() in (4, 5, 6) else random.choice([1, 2, 3])

        for s_idx in range(num_sales_today):
            inv_counter += 1
            inv_num = f"INV-2026-{inv_counter}"
            # Ensure unique invoice number
            while Sale.query.filter_by(invoice_number=inv_num).first():
                inv_counter += 1
                inv_num = f"INV-2026-{inv_counter}"

            sale_time = day_date.replace(
                hour=random.randint(9, 20),
                minute=random.randint(0, 59),
                second=random.randint(0, 59)
            )

            # Pick 1 to 3 distinct products for this transaction
            num_items = random.choices([1, 2, 3], weights=[0.55, 0.35, 0.10])[0]
            sampled_prods = random.sample(created_products, k=min(num_items, len(created_products)))

            subtotal = 0.0
            total_cost = 0.0
            sale_items = []

            for prod in sampled_prods:
                qty = random.choices([1, 2, 3], weights=[0.75, 0.20, 0.05])[0]
                unit_price = prod.selling_price
                unit_cost = prod.cost_price
                line_rev = round(unit_price * qty, 2)
                line_cst = round(unit_cost * qty, 2)
                line_prof = round(line_rev - line_cst, 2)

                subtotal += line_rev
                total_cost += line_cst

                item = SaleItem(
                    product_id=prod.id,
                    product_name=prod.name,
                    product_sku=prod.sku,
                    quantity=qty,
                    unit_cost_price=unit_cost,
                    unit_price=unit_price,
                    line_revenue=line_rev,
                    line_profit=line_prof
                )
                sale_items.append(item)

            # Discount logic (random 5% or 10% coupon occasionally)
            discount = 0.0
            if random.random() < 0.25 and subtotal > 100:
                discount = round(subtotal * random.choice([0.05, 0.10]), 2)

            tax = round((subtotal - discount) * 0.08, 2)  # 8% retail sales tax
            total_rev = round(subtotal - discount + tax, 2)
            est_profit = round(subtotal - discount - total_cost, 2)

            sale = Sale(
                invoice_number=inv_num,
                customer_name=random.choice(customers),
                channel=random.choice(channels),
                payment_method=random.choice(pay_methods),
                subtotal=round(subtotal, 2),
                discount=discount,
                tax=tax,
                total_revenue=total_rev,
                total_cost=round(total_cost, 2),
                estimated_profit=est_profit,
                notes="Standard retail checkout verified.",
                created_at=sale_time,
            )
            sale.items = sale_items
            db.session.add(sale)

    db.session.commit()
    return {
        "status": "success",
        "products_seeded": len(created_products),
        "categories_seeded": len(categories),
        "sales_seeded": inv_counter - 1001
    }
