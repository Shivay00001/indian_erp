"""
Indian SMB ERP - Data Models
CRUD operations for all business entities
"""
import json
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from decimal import Decimal
from database.db_init import get_database


class BaseModel:
    """Base model with common CRUD operations"""
    table_name = ""
    
    @classmethod
    def get_db(cls):
        return get_database()
    
    @classmethod
    def create(cls, data: Dict[str, Any]) -> int:
        db = cls.get_db()
        cursor = db.get_cursor()
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        cursor.execute(f"INSERT INTO {cls.table_name} ({columns}) VALUES ({placeholders})", list(data.values()))
        db.commit()
        return cursor.lastrowid
    
    @classmethod
    def get_by_id(cls, id: int) -> Optional[Dict]:
        cursor = cls.get_db().get_cursor()
        cursor.execute(f"SELECT * FROM {cls.table_name} WHERE id = ?", (id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    @classmethod
    def get_all(cls, where: str = None, params: tuple = None, order_by: str = "id DESC", limit: int = None) -> List[Dict]:
        cursor = cls.get_db().get_cursor()
        sql = f"SELECT * FROM {cls.table_name}"
        if where:
            sql += f" WHERE {where}"
        sql += f" ORDER BY {order_by}"
        if limit:
            sql += f" LIMIT {limit}"
        cursor.execute(sql, params or ())
        return [dict(row) for row in cursor.fetchall()]
    
    @classmethod
    def update(cls, id: int, data: Dict[str, Any]) -> bool:
        db = cls.get_db()
        cursor = db.get_cursor()
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        cursor.execute(f"UPDATE {cls.table_name} SET {set_clause} WHERE id = ?", list(data.values()) + [id])
        db.commit()
        return cursor.rowcount > 0
    
    @classmethod
    def delete(cls, id: int) -> bool:
        db = cls.get_db()
        cursor = db.get_cursor()
        cursor.execute(f"DELETE FROM {cls.table_name} WHERE id = ?", (id,))
        db.commit()
        return cursor.rowcount > 0
    
    @classmethod
    def count(cls, where: str = None, params: tuple = None) -> int:
        cursor = cls.get_db().get_cursor()
        sql = f"SELECT COUNT(*) FROM {cls.table_name}"
        if where:
            sql += f" WHERE {where}"
        cursor.execute(sql, params or ())
        return cursor.fetchone()[0]


class User(BaseModel):
    table_name = "users"
    
    @classmethod
    def get_by_username(cls, username: str) -> Optional[Dict]:
        cursor = cls.get_db().get_cursor()
        cursor.execute("SELECT u.*, r.name as role_name FROM users u JOIN roles r ON u.role_id = r.id WHERE u.username = ?", (username,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    @classmethod
    def update_last_login(cls, user_id: int):
        cls.update(user_id, {'last_login': datetime.now().isoformat()})


class Role(BaseModel):
    table_name = "roles"


class Permission(BaseModel):
    table_name = "permissions"
    
    @classmethod
    def get_by_role(cls, role_id: int) -> List[Dict]:
        cursor = cls.get_db().get_cursor()
        cursor.execute("SELECT * FROM permissions WHERE role_id = ?", (role_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    @classmethod
    def check_permission(cls, role_id: int, module: str, action: str) -> bool:
        cursor = cls.get_db().get_cursor()
        cursor.execute(f"SELECT {action} FROM permissions WHERE role_id = ? AND module = ?", (role_id, module))
        row = cursor.fetchone()
        return bool(row[0]) if row else False


class AuditLog(BaseModel):
    table_name = "audit_logs"
    
    @classmethod
    def log(cls, user_id: int, action: str, module: str, record_id: int = None, old_values: dict = None, new_values: dict = None):
        cls.create({
            'user_id': user_id,
            'action': action,
            'module': module,
            'record_id': record_id,
            'old_values': json.dumps(old_values) if old_values else None,
            'new_values': json.dumps(new_values) if new_values else None,
            'created_at': datetime.now().isoformat()
        })


class Product(BaseModel):
    table_name = "products"
    
    @classmethod
    def search(cls, query: str) -> List[Dict]:
        cursor = cls.get_db().get_cursor()
        cursor.execute("SELECT p.*, c.name as category_name, u.symbol as unit_symbol FROM products p LEFT JOIN categories c ON p.category_id = c.id LEFT JOIN units u ON p.unit_id = u.id WHERE p.name LIKE ? OR p.sku LIKE ? OR p.hsn_code LIKE ?",
                      (f"%{query}%", f"%{query}%", f"%{query}%"))
        return [dict(row) for row in cursor.fetchall()]
    
    @classmethod
    def get_low_stock(cls) -> List[Dict]:
        cursor = cls.get_db().get_cursor()
        cursor.execute("""SELECT p.*, COALESCE(SUM(i.quantity), 0) as current_stock FROM products p 
                         LEFT JOIN inventory i ON p.id = i.product_id WHERE p.is_active = 1 
                         GROUP BY p.id HAVING current_stock <= p.min_stock_level""")
        return [dict(row) for row in cursor.fetchall()]


class Inventory(BaseModel):
    table_name = "inventory"
    
    @classmethod
    def get_stock(cls, product_id: int) -> Decimal:
        cursor = cls.get_db().get_cursor()
        cursor.execute("SELECT COALESCE(SUM(quantity), 0) FROM inventory WHERE product_id = ?", (product_id,))
        return Decimal(str(cursor.fetchone()[0]))
    
    @classmethod
    def add_stock(cls, product_id: int, quantity: Decimal, batch: str = None, cost: Decimal = None, user_id: int = None):
        db = cls.get_db()
        cursor = db.get_cursor()
        cursor.execute("INSERT INTO inventory (product_id, quantity, batch_number, cost_price) VALUES (?, ?, ?, ?)",
                      (product_id, float(quantity), batch, float(cost) if cost else 0))
        cursor.execute("INSERT INTO stock_movements (product_id, movement_type, quantity, reference_type, user_id) VALUES (?, 'IN', ?, 'manual', ?)",
                      (product_id, float(quantity), user_id))
        db.commit()
    
    @classmethod
    def reduce_stock(cls, product_id: int, quantity: Decimal, reference_type: str = None, ref_id: int = None, user_id: int = None):
        db = cls.get_db()
        cursor = db.get_cursor()
        # FIFO reduction
        cursor.execute("SELECT id, quantity FROM inventory WHERE product_id = ? AND quantity > 0 ORDER BY created_at", (product_id,))
        remaining = float(quantity)
        for row in cursor.fetchall():
            if remaining <= 0:
                break
            reduce = min(remaining, row['quantity'])
            cursor.execute("UPDATE inventory SET quantity = quantity - ? WHERE id = ?", (reduce, row['id']))
            remaining -= reduce
        cursor.execute("INSERT INTO stock_movements (product_id, movement_type, quantity, reference_type, reference_id, user_id) VALUES (?, 'OUT', ?, ?, ?, ?)",
                      (product_id, float(quantity), reference_type, ref_id, user_id))
        db.commit()


class Customer(BaseModel):
    table_name = "customers"
    
    @classmethod
    def search(cls, query: str) -> List[Dict]:
        cursor = cls.get_db().get_cursor()
        cursor.execute("SELECT * FROM customers WHERE name LIKE ? OR company_name LIKE ? OR phone LIKE ? OR gstin LIKE ?",
                      tuple(f"%{query}%" for _ in range(4)))
        return [dict(row) for row in cursor.fetchall()]
    
    @classmethod
    def update_balance(cls, customer_id: int, amount: Decimal, add: bool = True):
        op = '+' if add else '-'
        cls.get_db().get_cursor().execute(f"UPDATE customers SET current_balance = current_balance {op} ? WHERE id = ?",
                                          (float(amount), customer_id))
        cls.get_db().commit()


class Vendor(BaseModel):
    table_name = "vendors"
    
    @classmethod
    def search(cls, query: str) -> List[Dict]:
        cursor = cls.get_db().get_cursor()
        cursor.execute("SELECT * FROM vendors WHERE name LIKE ? OR company_name LIKE ? OR phone LIKE ? OR gstin LIKE ?",
                      tuple(f"%{query}%" for _ in range(4)))
        return [dict(row) for row in cursor.fetchall()]


class Invoice(BaseModel):
    table_name = "invoices"
    
    @classmethod
    def get_next_number(cls, invoice_type: str) -> str:
        db = cls.get_db()
        cursor = db.get_cursor()
        today = datetime.now()
        fy = f"{today.year}-{str(today.year+1)[2:]}" if today.month >= 4 else f"{today.year-1}-{str(today.year)[2:]}"
        cursor.execute("SELECT last_number, prefix FROM invoice_sequences WHERE invoice_type = ? AND financial_year = ?", (invoice_type, fy))
        row = cursor.fetchone()
        if row:
            next_num = row['last_number'] + 1
            prefix = row['prefix']
            cursor.execute("UPDATE invoice_sequences SET last_number = ? WHERE invoice_type = ? AND financial_year = ?", (next_num, invoice_type, fy))
        else:
            prefix = invoice_type[:3]
            next_num = 1
            cursor.execute("INSERT INTO invoice_sequences (invoice_type, prefix, financial_year, last_number) VALUES (?, ?, ?, ?)",
                          (invoice_type, prefix, fy, 1))
        db.commit()
        return f"{prefix}/{fy}/{next_num:05d}"
    
    @classmethod
    def get_with_items(cls, invoice_id: int) -> Optional[Dict]:
        inv = cls.get_by_id(invoice_id)
        if inv:
            cursor = cls.get_db().get_cursor()
            cursor.execute("SELECT * FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
            inv['items'] = [dict(row) for row in cursor.fetchall()]
        return inv
    
    @classmethod
    def get_sales_summary(cls, start_date: str, end_date: str) -> Dict:
        cursor = cls.get_db().get_cursor()
        cursor.execute("""SELECT COUNT(*) as count, COALESCE(SUM(total_amount), 0) as total, 
                         COALESCE(SUM(cgst_amount + sgst_amount + igst_amount), 0) as gst
                         FROM invoices WHERE invoice_type = 'SALES' AND invoice_date BETWEEN ? AND ?""",
                      (start_date, end_date))
        return dict(cursor.fetchone())


class InvoiceItem(BaseModel):
    table_name = "invoice_items"


class Payment(BaseModel):
    table_name = "payments"
    
    @classmethod
    def get_next_number(cls) -> str:
        cursor = cls.get_db().get_cursor()
        cursor.execute("SELECT COUNT(*) + 1 FROM payments")
        return f"PAY/{datetime.now().strftime('%Y%m%d')}/{cursor.fetchone()[0]:05d}"


class Expense(BaseModel):
    table_name = "expenses"


class LedgerEntry(BaseModel):
    table_name = "ledger_entries"


class CompanySettings(BaseModel):
    table_name = "company_settings"
    
    @classmethod
    def get_settings(cls) -> Optional[Dict]:
        cursor = cls.get_db().get_cursor()
        cursor.execute("SELECT * FROM company_settings LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None
    
    @classmethod
    def save_settings(cls, data: Dict) -> int:
        existing = cls.get_settings()
        if existing:
            cls.update(existing['id'], data)
            return existing['id']
        return cls.create(data)


class Category(BaseModel):
    table_name = "categories"


class Unit(BaseModel):
    table_name = "units"


class PaymentMode(BaseModel):
    table_name = "payment_modes"
