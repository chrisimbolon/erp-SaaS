"""
scripts/seed_dev.py
====================
Seeds the development database with realistic data for PT Kusuma Lestari Agro.

Run: python scripts/seed_dev.py

Creates:
  ── Platform
     1 SuperAdmin         superadmin@kla.dev / Admin1234!

  ── Tenant: PT Kusuma Lestari Agro
     5 Users              owner / admin / sales / warehouse / finance
     8 Products           agricultural supplies with realistic stock levels
     3 Suppliers          fertilizer + pesticide + equipment vendors
     3 Customers          distribution companies

  ── Transactions
     2 Purchase Orders    (1 fully received, 1 partially received)
     2 Sales Orders       (1 fulfilled + invoiced + paid, 1 confirmed only)

All passwords: KLA_Dev_2026! (change in production)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.core.database import SessionLocal
from app.core.security import hash_password

# ─── Seed constants ───────────────────────────────────────────────────────────

DEFAULT_PASSWORD = "KLA_Dev_2026!"
NOW = datetime.now(timezone.utc)


def seed():
    db = SessionLocal()
    try:
        print("🌱 Seeding KLA development database...")
        print()

        # ── 1. SuperAdmin ─────────────────────────────────────────────────────
        from app.modules.tenants.infrastructure.models import UserModel, TenantModel

        superadmin = UserModel(
            tenant_id=None,
            email="superadmin@kla.dev",
            full_name="KLA Super Admin",
            role="super_admin",
            hashed_password=hash_password(DEFAULT_PASSWORD),
            is_active=True,
        )
        db.add(superadmin)
        db.flush()
        print(f"  ✓ SuperAdmin: superadmin@kla.dev")

        # ── 2. Tenant: PT Kusuma Lestari Agro ─────────────────────────────────
        tenant = TenantModel(
            name="PT Kusuma Lestari Agro",
            slug="pt-kusuma-lestari-agro",
            status="active",
            plan="pro",
            owner_email="chris@kusuma-agro.co.id",
            phone="+62-21-555-0101",
            address="Jl. Raya Bogor No. 88, Jakarta Timur 13710",
            npwp="01.234.567.8-901.000",
        )
        db.add(tenant)
        db.flush()
        TENANT_ID = tenant.id
        print(f"  ✓ Tenant: PT Kusuma Lestari Agro (id={TENANT_ID})")

        # ── 3. Tenant Users ────────────────────────────────────────────────────
        users_data = [
            ("chris@kusuma-agro.co.id",      "Chris Bolon",        "owner"),
            ("admin@kusuma-agro.co.id",      "Sari Dewi",          "admin"),
            ("sales@kusuma-agro.co.id",      "Budi Santoso",       "sales"),
            ("warehouse@kusuma-agro.co.id",  "Agus Wijaya",        "warehouse"),
            ("finance@kusuma-agro.co.id",    "Rina Kusuma",        "finance"),
        ]
        for email, name, role in users_data:
            u = UserModel(
                tenant_id=TENANT_ID, email=email, full_name=name,
                role=role, hashed_password=hash_password(DEFAULT_PASSWORD),
                is_active=True,
            )
            db.add(u)
        db.flush()
        print(f"  ✓ Users: {len(users_data)} tenant users created")

        # ── 4. Products ────────────────────────────────────────────────────────
        from app.modules.inventory.infrastructure.models import ProductModel

        products_data = [
            # sku,          name,                                  unit,  stock, min_stock, cost,     sell
            ("NPK-15",  "Pupuk NPK 15-15-15",                    "kg",  500,   100,       8500,    12000),
            ("UREA-46", "Pupuk Urea 46%",                        "kg",  800,   150,       6200,     9000),
            ("SP36-36", "Pupuk SP-36",                           "kg",  300,    80,       7800,    11000),
            ("KCL-60",  "Pupuk KCl 60%",                        "kg",  250,    60,       9500,    13500),
            ("RUP-ILG", "Pestisida Roundup ILG",                "liter", 80,   20,      45000,    68000),
            ("DUR-GRA", "Pestisida Dursban Granular",           "kg",   60,   15,      38000,    55000),
            ("CUR-EMU", "Curater Emulsifiable",                 "liter", 40,   10,      52000,    78000),
            ("HAND-SP", "Hand Sprayer 16L",                     "unit",  15,    5,     185000,   275000),
        ]

        product_ids = {}
        for sku, name, unit, stock, min_stock, cost, sell in products_data:
            p = ProductModel(
                tenant_id=TENANT_ID, sku=sku, name=name, unit=unit,
                current_stock=Decimal(str(stock)),
                minimum_stock=Decimal(str(min_stock)),
                cost_price=Decimal(str(cost)),
                sell_price=Decimal(str(sell)),
                is_active=True,
            )
            db.add(p)
            db.flush()
            product_ids[sku] = p.id

        print(f"  ✓ Products: {len(products_data)} products seeded")

        # ── 5. Suppliers ───────────────────────────────────────────────────────
        # Using a simple suppliers table (minimal — not full module yet)
        # We'll just insert directly for seed purposes

        from sqlalchemy import text
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS suppliers (
                id         SERIAL PRIMARY KEY,
                tenant_id  INTEGER NOT NULL,
                name       VARCHAR(255) NOT NULL,
                contact    VARCHAR(255),
                phone      VARCHAR(50),
                email      VARCHAR(255),
                address    TEXT,
                npwp       VARCHAR(30),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))

        suppliers_data = [
            (TENANT_ID, "PT Pupuk Kaltim",          "Hendra",  "+62-811-111-001", "hendra@pupukkaltim.com",   "Bontang, Kalimantan Timur"),
            (TENANT_ID, "CV Agro Kimia Nusantara",  "Dewi",    "+62-812-222-002", "dewi@agrokimia.co.id",     "Surabaya, Jawa Timur"),
            (TENANT_ID, "PT Sinar Tani Peralatan",  "Wahyu",   "+62-813-333-003", "wahyu@sinartani.co.id",    "Bandung, Jawa Barat"),
        ]
        supplier_ids = []
        for s in suppliers_data:
            result = db.execute(text("""
                INSERT INTO suppliers (tenant_id, name, contact, phone, email, address)
                VALUES (:tid, :name, :contact, :phone, :email, :address)
                RETURNING id
            """), {
                "tid": s[0], "name": s[1], "contact": s[2],
                "phone": s[3], "email": s[4], "address": s[5],
            })
            supplier_ids.append(result.scalar())
        print(f"  ✓ Suppliers: {len(supplier_ids)} seeded")

        # ── 6. Customers ───────────────────────────────────────────────────────
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS customers (
                id         SERIAL PRIMARY KEY,
                tenant_id  INTEGER NOT NULL,
                name       VARCHAR(255) NOT NULL,
                contact    VARCHAR(255),
                phone      VARCHAR(50),
                email      VARCHAR(255),
                address    TEXT,
                npwp       VARCHAR(30),
                credit_limit NUMERIC(15,2) DEFAULT 50000000,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))

        customers_data = [
            (TENANT_ID, "UD Tani Makmur Sejahtera", "Pak Joko",  "+62-821-001-001", "joko@tanimakmur.com",    "Bekasi, Jawa Barat",    75000000),
            (TENANT_ID, "CV Hasil Bumi Nusantara",  "Bu Siti",   "+62-822-002-002", "siti@hasilbumi.co.id",   "Karawang, Jawa Barat",  50000000),
            (TENANT_ID, "PT Agro Distribusi Jaya",  "Pak Hasan", "+62-823-003-003", "hasan@agrodistribusi.com", "Cirebon, Jawa Barat", 100000000),
        ]
        customer_ids = []
        for c in customers_data:
            result = db.execute(text("""
                INSERT INTO customers (tenant_id, name, contact, phone, email, address, credit_limit)
                VALUES (:tid, :name, :contact, :phone, :email, :address, :limit)
                RETURNING id
            """), {
                "tid": c[0], "name": c[1], "contact": c[2],
                "phone": c[3], "email": c[4], "address": c[5], "limit": c[6],
            })
            customer_ids.append(result.scalar())
        print(f"  ✓ Customers: {len(customer_ids)} seeded")

        # ── 7. Purchase Orders ─────────────────────────────────────────────────
        from app.modules.purchase.infrastructure.models import (
            PurchaseOrderModel, PurchaseOrderItemModel, GoodsReceiptModel
        )
        from app.modules.inventory.infrastructure.models import StockMovementModel

        # PO 1 — Fully received (created 10 days ago)
        po1 = PurchaseOrderModel(
            tenant_id=TENANT_ID, supplier_id=supplier_ids[0],
            po_number=f"PO/2026/04/0001",
            status="fully_received",
            order_date=NOW - timedelta(days=10),
            expected_delivery=NOW - timedelta(days=7),
            notes="Pesanan rutin pupuk NPK dan Urea",
        )
        db.add(po1)
        db.flush()

        po1_items = [
            (product_ids["NPK-15"],  "Pupuk NPK 15-15-15", Decimal("200"), Decimal("8500"), "kg"),
            (product_ids["UREA-46"], "Pupuk Urea 46%",     Decimal("300"), Decimal("6200"), "kg"),
        ]
        for pid, pname, qty, price, unit in po1_items:
            db.add(PurchaseOrderItemModel(
                tenant_id=TENANT_ID, purchase_order_id=po1.id,
                product_id=pid, product_name=pname,
                quantity_ordered=qty, unit_price=price, unit=unit,
            ))

        # Goods receipt for PO1
        gr1 = GoodsReceiptModel(
            tenant_id=TENANT_ID, purchase_order_id=po1.id,
            receipt_number="GR/2026/04/0001", status="completed",
            received_date=NOW - timedelta(days=7), received_by=1,
            notes="Barang diterima lengkap, kondisi baik",
        )
        db.add(gr1)
        db.flush()

        # Stock movements for PO1
        for pid, pname, qty, price, unit in po1_items:
            stock_before = Decimal("300") if pid == product_ids["NPK-15"] else Decimal("500")
            db.add(StockMovementModel(
                tenant_id=TENANT_ID, product_id=pid,
                movement_type="in", quantity=qty,
                stock_before=stock_before,
                stock_after=stock_before + qty,
                reference_type="goods_receipt",
                reference_id=gr1.id, reference_number="GR/2026/04/0001",
                movement_date=NOW - timedelta(days=7),
                notes="Penerimaan barang PO/2026/04/0001",
            ))

        # PO 2 — Partially received (created 3 days ago)
        po2 = PurchaseOrderModel(
            tenant_id=TENANT_ID, supplier_id=supplier_ids[1],
            po_number="PO/2026/04/0002",
            status="partially_received",
            order_date=NOW - timedelta(days=3),
            expected_delivery=NOW + timedelta(days=2),
            notes="Pestisida untuk musim tanam",
        )
        db.add(po2)
        db.flush()

        po2_items = [
            (product_ids["RUP-ILG"], "Pestisida Roundup ILG",        Decimal("50"), Decimal("45000"), "liter"),
            (product_ids["DUR-GRA"], "Pestisida Dursban Granular",    Decimal("40"), Decimal("38000"), "kg"),
            (product_ids["CUR-EMU"], "Curater Emulsifiable",          Decimal("30"), Decimal("52000"), "liter"),
        ]
        for pid, pname, qty, price, unit in po2_items:
            db.add(PurchaseOrderItemModel(
                tenant_id=TENANT_ID, purchase_order_id=po2.id,
                product_id=pid, product_name=pname,
                quantity_ordered=qty, unit_price=price, unit=unit,
            ))

        # Partial receipt — only first two items received
        gr2 = GoodsReceiptModel(
            tenant_id=TENANT_ID, purchase_order_id=po2.id,
            receipt_number="GR/2026/04/0002", status="completed",
            received_date=NOW - timedelta(days=1), received_by=1,
            notes="Barang Roundup dan Dursban sudah tiba. Curater menyusul.",
        )
        db.add(gr2)
        db.flush()

        for pid, pname, qty, price, unit in po2_items[:2]:
            stock_before = Decimal("30") if pid == product_ids["RUP-ILG"] else Decimal("20")
            db.add(StockMovementModel(
                tenant_id=TENANT_ID, product_id=pid,
                movement_type="in", quantity=qty,
                stock_before=stock_before,
                stock_after=stock_before + qty,
                reference_type="goods_receipt",
                reference_id=gr2.id, reference_number="GR/2026/04/0002",
                movement_date=NOW - timedelta(days=1),
                notes="Penerimaan parsial PO/2026/04/0002",
            ))

        print(f"  ✓ Purchase Orders: 2 POs, 2 Goods Receipts, stock movements seeded")

        # ── 8. Sales Orders ────────────────────────────────────────────────────
        from app.modules.sales.infrastructure.models import (
            SalesOrderModel, SalesOrderItemModel,
            SuratJalanModel, SuratJalanItemModel,
            InvoiceModel, PaymentModel,
        )
        from app.modules.inventory.infrastructure.models import StockReservationModel

        # SO 1 — Fully completed: fulfilled + invoiced + paid (5 days ago)
        so1 = SalesOrderModel(
            tenant_id=TENANT_ID, customer_id=customer_ids[0],
            order_number="SO/2026/04/0001", status="fulfilled",
            order_date=NOW - timedelta(days=5), created_by=1,
            notes="Pesanan rutin UD Tani Makmur",
        )
        db.add(so1)
        db.flush()

        so1_items_data = [
            (product_ids["NPK-15"],  "Pupuk NPK 15-15-15", 1, Decimal("100"), Decimal("12000"), "kg",   Decimal("0")),
            (product_ids["UREA-46"], "Pupuk Urea 46%",     2, Decimal("150"), Decimal("9000"),  "kg",   Decimal("5")),
            (product_ids["SP36-36"], "Pupuk SP-36",        3, Decimal("80"),  Decimal("11000"), "kg",   Decimal("0")),
        ]
        so1_item_ids = []
        for pid, pname, idx, qty, price, unit, disc in so1_items_data:
            item = SalesOrderItemModel(
                tenant_id=TENANT_ID, sales_order_id=so1.id,
                product_id=pid, product_name=pname,
                quantity=qty, unit_price=price, unit=unit, discount_pct=disc,
            )
            db.add(item)
            db.flush()
            so1_item_ids.append((item.id, pid, qty, unit, price))

        # Surat Jalan for SO1
        sj1 = SuratJalanModel(
            tenant_id=TENANT_ID, sales_order_id=so1.id,
            sj_number="SJ/2026/04/0001", status="issued",
            issued_date=NOW - timedelta(days=4), issued_by=1,
            notes="Dikirim via Wahana Express",
        )
        db.add(sj1)
        db.flush()

        for item_id, pid, qty, unit, price in so1_item_ids:
            db.add(SuratJalanItemModel(
                tenant_id=TENANT_ID, surat_jalan_id=sj1.id,
                sales_order_item_id=item_id,
                product_id=pid, quantity_shipped=qty, unit=unit,
            ))
            # Stock movement OUT
            stock_before = Decimal("500") if pid == product_ids["NPK-15"] else (
                Decimal("800") if pid == product_ids["UREA-46"] else Decimal("300")
            )
            db.add(StockMovementModel(
                tenant_id=TENANT_ID, product_id=pid,
                movement_type="out", quantity=qty,
                stock_before=stock_before,
                stock_after=stock_before - qty,
                reference_type="surat_jalan",
                reference_id=sj1.id, reference_number="SJ/2026/04/0001",
                movement_date=NOW - timedelta(days=4),
                notes=f"Pengiriman SO/2026/04/0001 ke UD Tani Makmur",
            ))

        # Invoice for SO1
        subtotal_so1 = (
            Decimal("100") * Decimal("12000") +
            Decimal("150") * Decimal("9000") * Decimal("0.95") +
            Decimal("80")  * Decimal("11000")
        )
        tax_so1 = (subtotal_so1 * Decimal("0.11")).quantize(Decimal("0.01"))
        total_so1 = subtotal_so1 + tax_so1

        inv1 = InvoiceModel(
            tenant_id=TENANT_ID, sales_order_id=so1.id, customer_id=customer_ids[0],
            invoice_number="INV/2026/04/0001", status="paid",
            subtotal=subtotal_so1, tax_amount=tax_so1, total_amount=total_so1,
            issue_date=NOW - timedelta(days=4),
            due_date=NOW - timedelta(days=4) + timedelta(days=30),
            notes="NET 30",
        )
        db.add(inv1)
        db.flush()

        # Payment for INV1
        db.add(PaymentModel(
            tenant_id=TENANT_ID, invoice_id=inv1.id,
            payment_number="PAY/2026/04/0001",
            amount=total_so1, payment_method="bank_transfer",
            payment_date=NOW - timedelta(days=2),
            reference_no="TRF-BCA-20260419-001",
            notes="Transfer BCA dari UD Tani Makmur",
        ))

        # SO 2 — Confirmed only (stock reserved, awaiting Surat Jalan)
        so2 = SalesOrderModel(
            tenant_id=TENANT_ID, customer_id=customer_ids[2],
            order_number="SO/2026/04/0002", status="confirmed",
            order_date=NOW - timedelta(days=1), created_by=1,
            notes="Pesanan PT Agro Distribusi",
        )
        db.add(so2)
        db.flush()

        so2_items_data = [
            (product_ids["KCL-60"],  "Pupuk KCl 60%",  Decimal("80"),  Decimal("13500"), "kg",    Decimal("0")),
            (product_ids["HAND-SP"], "Hand Sprayer 16L", Decimal("5"),  Decimal("275000"), "unit", Decimal("10")),
        ]
        for pid, pname, qty, price, unit, disc in so2_items_data:
            db.add(SalesOrderItemModel(
                tenant_id=TENANT_ID, sales_order_id=so2.id,
                product_id=pid, product_name=pname,
                quantity=qty, unit_price=price, unit=unit, discount_pct=disc,
            ))
            # Create active reservation
            db.add(StockReservationModel(
                tenant_id=TENANT_ID, product_id=pid,
                sales_order_id=so2.id, order_number="SO/2026/04/0002",
                quantity_reserved=qty, is_active=True,
            ))

        print(f"  ✓ Sales Orders: 2 SOs (1 paid, 1 confirmed+reserved)")

        # ── Commit everything ─────────────────────────────────────────────────
        db.commit()

        print()
        print("━" * 55)
        print("  ✅  Seed complete!")
        print("━" * 55)
        print()
        print("  Login credentials (all passwords: KLA_Dev_2026!)")
        print()
        print("  Role           Email")
        print("  ─────────────  ──────────────────────────────────")
        print("  super_admin    superadmin@kla.dev")
        print("  owner          chris@kusuma-agro.co.id")
        print("  admin          admin@kusuma-agro.co.id")
        print("  sales          sales@kusuma-agro.co.id")
        print("  warehouse      warehouse@kusuma-agro.co.id")
        print("  finance        finance@kusuma-agro.co.id")
        print()
        print("  API docs → http://localhost:8000/docs")
        print("━" * 55)

    except Exception as e:
        db.rollback()
        print(f"\n  ❌  Seed failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    seed()
