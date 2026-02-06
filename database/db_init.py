"""
Indian SMB ERP - Database Initialization
Auto-creates SQLite database with complete schema on first run
"""
import sqlite3
import os
import shutil
from datetime import datetime
import hashlib
import bcrypt


class DatabaseManager:
    """Manages SQLite database creation, connection, and backup"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            app_data = os.path.join(os.path.expanduser("~"), ".indian_erp")
            os.makedirs(app_data, exist_ok=True)
            db_path = os.path.join(app_data, "erp_data.db")
        
        self.db_path = db_path
        self.backup_dir = os.path.join(os.path.dirname(db_path), "backups")
        os.makedirs(self.backup_dir, exist_ok=True)
        self._connection = None
        self._initialize_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path)
            self._connection.execute("PRAGMA foreign_keys = ON")
            self._connection.execute("PRAGMA journal_mode = WAL")  # Enable WAL mode for concurrency/stability
            self._connection.execute("PRAGMA synchronous = NORMAL") # Good balance for WAL
            self._connection.row_factory = sqlite3.Row
        return self._connection
    
    def get_cursor(self) -> sqlite3.Cursor:
        return self._get_connection().cursor()
    
    def commit(self):
        self._get_connection().commit()
    
    def rollback(self):
        self._get_connection().rollback()
    
    def close(self):
        if self._connection:
            self._connection.close()
            self._connection = None
    
    def _initialize_database(self):
        """Create all tables if they don't exist"""
        cursor = self.get_cursor()
        self._create_core_tables(cursor)
        self._create_business_tables(cursor)
        self._create_indexes(cursor)
        self.commit()
        self._insert_default_data()
    
    def _create_core_tables(self, cursor):
        """Create core system tables"""
        # Roles
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(50) UNIQUE NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        
        # Users
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(200),
                email VARCHAR(200),
                phone VARCHAR(20),
                role_id INTEGER NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (role_id) REFERENCES roles(id)
            )""")
        
        # Permissions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role_id INTEGER NOT NULL,
                module VARCHAR(50) NOT NULL,
                can_view BOOLEAN DEFAULT 0,
                can_create BOOLEAN DEFAULT 0,
                can_edit BOOLEAN DEFAULT 0,
                can_delete BOOLEAN DEFAULT 0,
                can_export BOOLEAN DEFAULT 0,
                FOREIGN KEY (role_id) REFERENCES roles(id),
                UNIQUE(role_id, module)
            )""")
        
        # Audit logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action VARCHAR(50) NOT NULL,
                module VARCHAR(50),
                record_id INTEGER,
                old_values TEXT,
                new_values TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )""")
        
        # Company settings with UPI/Payment gateway
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS company_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name VARCHAR(200),
                address TEXT,
                city VARCHAR(100),
                state VARCHAR(100),
                state_code VARCHAR(10),
                pincode VARCHAR(10),
                phone VARCHAR(20),
                email VARCHAR(200),
                gstin VARCHAR(15),
                pan VARCHAR(10),
                logo_path TEXT,
                upi_qr_path TEXT,
                upi_id VARCHAR(100),
                payment_gateway VARCHAR(50),
                payment_api_key TEXT,
                payment_api_secret TEXT,
                invoice_prefix VARCHAR(20) DEFAULT 'INV',
                invoice_start_number INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        
        # License
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS license (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_key VARCHAR(100) UNIQUE NOT NULL,
                machine_fingerprint VARCHAR(255),
                plan_type VARCHAR(50) NOT NULL,
                max_users INTEGER DEFAULT 1,
                enabled_modules TEXT,
                activation_date DATE,
                expiry_date DATE,
                is_active BOOLEAN DEFAULT 1,
                grace_period_days INTEGER DEFAULT 7
            )""")
        
        # Backup history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS backup_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backup_path TEXT NOT NULL,
                backup_type VARCHAR(20) NOT NULL,
                file_size INTEGER,
                checksum VARCHAR(64),
                user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
    
    def _create_business_tables(self, cursor):
        """Create business entity tables"""
        # Categories & Units
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                parent_id INTEGER,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (parent_id) REFERENCES categories(id)
            )""")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS units (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(50) NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                is_active BOOLEAN DEFAULT 1
            )""")
        
        # Products
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(200) NOT NULL,
                sku VARCHAR(50) UNIQUE,
                hsn_code VARCHAR(20),
                category_id INTEGER,
                unit_id INTEGER,
                purchase_price DECIMAL(15,2) DEFAULT 0,
                selling_price DECIMAL(15,2) DEFAULT 0,
                gst_rate DECIMAL(5,2) DEFAULT 18,
                min_stock_level INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id),
                FOREIGN KEY (unit_id) REFERENCES units(id)
            )""")
        
        # Inventory
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                quantity DECIMAL(15,3) DEFAULT 0,
                batch_number VARCHAR(50),
                expiry_date DATE,
                cost_price DECIMAL(15,2) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )""")
        
        # Stock movements
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                movement_type VARCHAR(20) NOT NULL,
                quantity DECIMAL(15,3) NOT NULL,
                reference_type VARCHAR(50),
                reference_id INTEGER,
                user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )""")
        
        # Customers
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(200) NOT NULL,
                company_name VARCHAR(200),
                gstin VARCHAR(15),
                address TEXT,
                city VARCHAR(100),
                state VARCHAR(100),
                state_code VARCHAR(10),
                phone VARCHAR(20),
                email VARCHAR(200),
                credit_limit DECIMAL(15,2) DEFAULT 0,
                credit_period INTEGER DEFAULT 0,
                current_balance DECIMAL(15,2) DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        
        # Vendors
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vendors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(200) NOT NULL,
                company_name VARCHAR(200),
                gstin VARCHAR(15),
                address TEXT,
                city VARCHAR(100),
                state VARCHAR(100),
                state_code VARCHAR(10),
                phone VARCHAR(20),
                email VARCHAR(200),
                current_balance DECIMAL(15,2) DEFAULT 0,
                bank_name VARCHAR(100),
                bank_account VARCHAR(50),
                bank_ifsc VARCHAR(20),
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        
        # Invoices
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number VARCHAR(50) UNIQUE NOT NULL,
                invoice_type VARCHAR(20) NOT NULL,
                customer_id INTEGER,
                vendor_id INTEGER,
                invoice_date DATE NOT NULL,
                due_date DATE,
                supply_state_code VARCHAR(10),
                is_igst BOOLEAN DEFAULT 0,
                subtotal DECIMAL(15,2) DEFAULT 0,
                cgst_amount DECIMAL(15,2) DEFAULT 0,
                sgst_amount DECIMAL(15,2) DEFAULT 0,
                igst_amount DECIMAL(15,2) DEFAULT 0,
                total_amount DECIMAL(15,2) DEFAULT 0,
                amount_paid DECIMAL(15,2) DEFAULT 0,
                payment_status VARCHAR(20) DEFAULT 'unpaid',
                status VARCHAR(20) DEFAULT 'draft',
                user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id),
                FOREIGN KEY (vendor_id) REFERENCES vendors(id)
            )""")
        
        # Invoice items
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoice_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                product_id INTEGER,
                description TEXT,
                hsn_code VARCHAR(20),
                quantity DECIMAL(15,3) DEFAULT 1,
                rate DECIMAL(15,2) DEFAULT 0,
                gst_rate DECIMAL(5,2) DEFAULT 0,
                cgst_amount DECIMAL(15,2) DEFAULT 0,
                sgst_amount DECIMAL(15,2) DEFAULT 0,
                igst_amount DECIMAL(15,2) DEFAULT 0,
                total_amount DECIMAL(15,2) DEFAULT 0,
                FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )""")
        
        # Payment modes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payment_modes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(50) NOT NULL,
                type VARCHAR(20),
                is_active BOOLEAN DEFAULT 1
            )""")
        
        # Payments
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payment_number VARCHAR(50) UNIQUE NOT NULL,
                payment_type VARCHAR(20) NOT NULL,
                customer_id INTEGER,
                vendor_id INTEGER,
                invoice_id INTEGER,
                payment_date DATE NOT NULL,
                amount DECIMAL(15,2) NOT NULL,
                payment_mode_id INTEGER,
                reference_number VARCHAR(100),
                upi_transaction_id VARCHAR(100),
                payment_gateway_ref VARCHAR(100),
                status VARCHAR(20) DEFAULT 'completed',
                user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id),
                FOREIGN KEY (invoice_id) REFERENCES invoices(id)
            )""")
        
        # Expenses
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_number VARCHAR(50) UNIQUE NOT NULL,
                expense_date DATE NOT NULL,
                category VARCHAR(100),
                vendor_id INTEGER,
                description TEXT,
                amount DECIMAL(15,2) NOT NULL,
                gst_amount DECIMAL(15,2) DEFAULT 0,
                total_amount DECIMAL(15,2) NOT NULL,
                payment_mode_id INTEGER,
                user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        
        # Ledger entries
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ledger_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_date DATE NOT NULL,
                account_type VARCHAR(50) NOT NULL,
                reference_type VARCHAR(50),
                reference_id INTEGER,
                customer_id INTEGER,
                vendor_id INTEGER,
                description TEXT,
                debit_amount DECIMAL(15,2) DEFAULT 0,
                credit_amount DECIMAL(15,2) DEFAULT 0,
                user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        
        # Invoice sequences
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoice_sequences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_type VARCHAR(20) NOT NULL,
                prefix VARCHAR(20),
                financial_year VARCHAR(10),
                last_number INTEGER DEFAULT 0,
                UNIQUE(invoice_type, financial_year)
            )""")
    
    def _create_indexes(self, cursor):
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_date ON invoices(invoice_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_customer ON invoices(customer_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_date ON payments(payment_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_product ON stock_movements(product_id)")
    
    def _insert_default_data(self):
        """Insert default roles, units, and admin user"""
        cursor = self.get_cursor()
        
        # Default roles
        roles = [('Admin', 'Full access'), ('Manager', 'Management'), 
                 ('Accountant', 'Accounting'), ('Sales', 'Sales'), ('Inventory', 'Inventory')]
        for name, desc in roles:
            cursor.execute("INSERT OR IGNORE INTO roles (name, description) VALUES (?, ?)", (name, desc))
        
        # Default units  
        units = [('Pieces', 'PCS'), ('Kilograms', 'KG'), ('Grams', 'GM'), ('Litres', 'LTR'),
                 ('Meters', 'MTR'), ('Dozen', 'DZN'), ('Box', 'BOX'), ('Numbers', 'NOS')]
        for name, symbol in units:
            cursor.execute("INSERT OR IGNORE INTO units (name, symbol) VALUES (?, ?)", (name, symbol))
        
        # Payment modes
        modes = [('Cash', 'cash'), ('Bank Transfer', 'bank'), ('UPI', 'upi'), 
                 ('Cheque', 'cheque'), ('Card', 'card'), ('Payment Gateway', 'gateway')]
        for name, mtype in modes:
            cursor.execute("INSERT OR IGNORE INTO payment_modes (name, type) VALUES (?, ?)", (name, mtype))
        
        # Admin user
        admin_hash = bcrypt.hashpw(b'admin123', bcrypt.gensalt()).decode('utf-8')
        cursor.execute("""INSERT OR IGNORE INTO users (username, password_hash, full_name, role_id, is_active)
                         SELECT 'admin', ?, 'Administrator', id, 1 FROM roles WHERE name='Admin'""", (admin_hash,))
        
        # Admin permissions
        cursor.execute("SELECT id FROM roles WHERE name='Admin'")
        admin = cursor.fetchone()
        if admin:
            for mod in ['dashboard','billing','inventory','customers','vendors','accounts','reports','settings','users']:
                cursor.execute("""INSERT OR IGNORE INTO permissions (role_id, module, can_view, can_create, can_edit, can_delete, can_export)
                                 VALUES (?, ?, 1, 1, 1, 1, 1)""", (admin['id'], mod))
        self.commit()
    
    # Backup methods
    def create_backup(self, backup_type: str = 'manual', user_id: int = None) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(self.backup_dir, f"erp_backup_{backup_type}_{timestamp}.db")
        self.close()
        try:
            shutil.copy2(self.db_path, backup_path)
            checksum = hashlib.sha256(open(backup_path, 'rb').read()).hexdigest()
            self._connection = None
            cursor = self.get_cursor()
            cursor.execute("INSERT INTO backup_history (backup_path, backup_type, file_size, checksum, user_id) VALUES (?, ?, ?, ?, ?)",
                          (backup_path, backup_type, os.path.getsize(backup_path), checksum, user_id))
            self.commit()
            return backup_path
        except Exception as e:
            self._connection = None
            raise Exception(f"Backup failed: {e}")
    
    def restore_backup(self, backup_path: str) -> bool:
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Backup not found: {backup_path}")
        self.close()
        try:
            pre_restore = os.path.join(self.backup_dir, f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
            if os.path.exists(self.db_path):
                shutil.copy2(self.db_path, pre_restore)
            shutil.copy2(backup_path, self.db_path)
            self._connection = None
            return True
        except Exception as e:
            self._connection = None
            raise Exception(f"Restore failed: {e}")
    
    def get_backup_list(self) -> list:
        cursor = self.get_cursor()
        cursor.execute("SELECT * FROM backup_history ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]


_db_instance = None

def get_database() -> DatabaseManager:
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance
