"""
Indian SMB ERP - License Management System
Machine fingerprint, license validation, and module control
"""
import hashlib
import platform
import uuid
import json
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List
from database.db_init import get_database


class LicenseError(Exception):
    """License related errors"""
    pass


class MachineFingerprint:
    """Generate unique machine identifier"""
    
    @staticmethod
    def generate() -> str:
        """Generate a unique fingerprint based on machine hardware"""
        components = [
            platform.node(),
            platform.machine(),
            platform.processor(),
            str(uuid.getnode()),
        ]
        fingerprint_str = '|'.join(components)
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()[:32]
    
    @staticmethod
    def verify(stored_fingerprint: str) -> bool:
        """Verify current machine matches stored fingerprint"""
        return MachineFingerprint.generate() == stored_fingerprint


class LicensePlans:
    """License plan definitions"""
    BASIC = 'BASIC'
    PRO = 'PRO'
    ENTERPRISE = 'ENTERPRISE'
    TRIAL = 'TRIAL'
    
    PLAN_CONFIG = {
        TRIAL: {
            'name': 'Trial',
            'max_users': 1,
            'modules': ['dashboard', 'billing', 'inventory'],
            'duration_days': 30,
            'price': 0
        },
        BASIC: {
            'name': 'Basic ERP',
            'max_users': 1,
            'modules': ['dashboard', 'billing', 'inventory', 'customers'],
            'duration_days': 365,
            'price': 4999
        },
        PRO: {
            'name': 'Pro ERP',
            'max_users': 3,
            'modules': ['dashboard', 'billing', 'inventory', 'customers', 'vendors', 'accounts', 'reports'],
            'duration_days': 365,
            'price': 9999
        },
        ENTERPRISE: {
            'name': 'Enterprise ERP',
            'max_users': 999,
            'modules': ['dashboard', 'billing', 'inventory', 'customers', 'vendors', 'accounts', 'reports', 'settings', 'users'],
            'duration_days': 365,
            'price': 24999
        }
    }


class LicenseManager:
    """Manages license activation, validation, and enforcement"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._license = None
            cls._instance._load_license()
        return cls._instance
    
    def _load_license(self):
        """Load license from database"""
        db = get_database()
        cursor = db.get_cursor()
        cursor.execute("SELECT * FROM license WHERE is_active = 1 ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            self._license = dict(row)
            if self._license.get('enabled_modules'):
                try:
                    self._license['modules_list'] = json.loads(self._license['enabled_modules'])
                except:
                    self._license['modules_list'] = []
    
    @property
    def is_activated(self) -> bool:
        return self._license is not None
    
    @property
    def is_valid(self) -> bool:
        if not self._license:
            return False
            
        # Check if revoked locally
        if self._license.get('is_revoked'):
            return False
        
        # Check machine fingerprint
        if self._license.get('machine_fingerprint'):
            if not MachineFingerprint.verify(self._license['machine_fingerprint']):
                return False
        
        # Check expiry with grace period
        if self._license.get('expiry_date'):
            expiry = datetime.strptime(str(self._license['expiry_date']), '%Y-%m-%d').date()
            grace = self._license.get('grace_period_days', 7)
            final_expiry = expiry + timedelta(days=grace)
            if date.today() > final_expiry:
                return False
        
        return True

    def check_remote_revocation(self, revocation_url: str = None) -> bool:
        """
        Check remote server for revoked keys/machines using Kill Switch logic.
        Returns True if license was revoked during this check.
        """
        if not self._license or not self.is_activated or not revocation_url:
            return False
            
        try:
            import requests
            # Expecting JSON list of revoked keys or machine IDs
            # Example: {"revoked_keys": ["BASI-1234..."], "revoked_machines": ["..."]}
            response = requests.get(revocation_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                current_key = self._license['license_key']
                current_machine = self._license.get('machine_fingerprint', '')
                
                if (current_key in data.get('revoked_keys', []) or 
                    current_machine in data.get('revoked_machines', [])):
                    
                    # Kill Switch Activated
                    self.revoke_license()
                    return True
        except Exception as e:
            # On network error, we don't block access (fail open) unless strictly required
            print(f"Revocation check failed: {e}")
            
        return False

    def revoke_license(self):
        """Locally revoke the license (Kill Switch action)"""
        db = get_database()
        cursor = db.get_cursor()
        cursor.execute("UPDATE license SET is_active = 0, is_revoked = 1 WHERE id = ?", (self._license['id'],))
        db.commit()
        self._license = None

    
    @property
    def plan_type(self) -> str:
        return self._license.get('plan_type', 'NONE') if self._license else 'NONE'
    
    @property
    def plan_name(self) -> str:
        plan = self.plan_type
        return LicensePlans.PLAN_CONFIG.get(plan, {}).get('name', 'No License')
    
    @property
    def max_users(self) -> int:
        return self._license.get('max_users', 1) if self._license else 1
    
    def get_enabled_modules(self) -> List[str]:
        if not self._license:
            return []
        return self._license.get('modules_list', [])
    
    def is_module_enabled(self, module: str) -> bool:
        if not self.is_valid:
            return False
        return module in self.get_enabled_modules()
    
    def get_status(self) -> Dict:
        """Get complete license status"""
        return {
            'activated': self.is_activated,
            'valid': self.is_valid,
            'expired': self.is_expired,
            'plan': self.plan_type,
            'plan_name': self.plan_name,
            'days_remaining': self.days_remaining,
            'max_users': self.max_users,
            'modules': self.get_enabled_modules(),
            'machine_bound': bool(self._license.get('machine_fingerprint') if self._license else False)
        }
    
    def activate(self, license_key: str) -> Dict:
        """Activate a license key"""
        # Validate license key format
        if not self._validate_key_format(license_key):
            raise LicenseError("Invalid license key format")
        
        # Decode license key
        license_data = self._decode_license_key(license_key)
        if not license_data:
            raise LicenseError("Invalid or corrupted license key")
        
        # Check if already activated on another machine
        db = get_database()
        cursor = db.get_cursor()
        cursor.execute("SELECT machine_fingerprint FROM license WHERE license_key = ?", (license_key,))
        existing = cursor.fetchone()
        if existing and existing['machine_fingerprint']:
            current_fp = MachineFingerprint.generate()
            if existing['machine_fingerprint'] != current_fp:
                raise LicenseError("License already activated on another machine")
        
        # Prepare license record
        machine_fp = MachineFingerprint.generate()
        plan = license_data.get('plan', LicensePlans.BASIC)
        plan_config = LicensePlans.PLAN_CONFIG.get(plan, LicensePlans.PLAN_CONFIG[LicensePlans.BASIC])
        
        expiry_date = license_data.get('expiry')
        if not expiry_date:
            expiry_date = (date.today() + timedelta(days=plan_config['duration_days'])).isoformat()
        
        modules = license_data.get('modules', plan_config['modules'])
        
        license_record = {
            'license_key': license_key,
            'machine_fingerprint': machine_fp,
            'plan_type': plan,
            'max_users': license_data.get('max_users', plan_config['max_users']),
            'enabled_modules': json.dumps(modules),
            'activation_date': date.today().isoformat(),
            'expiry_date': expiry_date,
            'is_active': True,
            'grace_period_days': 7
        }
        
        # Deactivate old licenses
        cursor.execute("UPDATE license SET is_active = 0")
        
        # Insert new license
        cols = ', '.join(license_record.keys())
        vals = ', '.join(['?' for _ in license_record])
        cursor.execute(f"INSERT INTO license ({cols}) VALUES ({vals})", list(license_record.values()))
        db.commit()
        
        self._load_license()
        return self.get_status()
    
    def _validate_key_format(self, key: str) -> bool:
        """Validate license key format: XXXX-XXXX-XXXX-XXXX"""
        import re
        pattern = r'^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$'
        return bool(re.match(pattern, key.upper()))
    
    def _decode_license_key(self, key: str) -> Optional[Dict]:
        """Decode license key to extract plan and settings"""
        # Simple encoding scheme: first 4 chars indicate plan
        key = key.upper().replace('-', '')
        if len(key) != 16:
            return None
        
        plan_codes = {
            'TRIA': LicensePlans.TRIAL,
            'BASI': LicensePlans.BASIC,
            'PROF': LicensePlans.PRO,
            'ENTR': LicensePlans.ENTERPRISE,
        }
        
        plan_code = key[:4]
        plan = plan_codes.get(plan_code, LicensePlans.BASIC)
        
        return {'plan': plan}
    
    def generate_license_key(self, plan: str, custom_modules: List[str] = None) -> str:
        """Generate a new license key (for admin/vendor use)"""
        import random
        import string
        
        plan_codes = {
            LicensePlans.TRIAL: 'TRIA',
            LicensePlans.BASIC: 'BASI',
            LicensePlans.PRO: 'PROF',
            LicensePlans.ENTERPRISE: 'ENTR',
        }
        
        plan_code = plan_codes.get(plan, 'BASI')
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
        key = plan_code + random_part
        return f"{key[:4]}-{key[4:8]}-{key[8:12]}-{key[12:16]}"
    
    def start_trial(self) -> Dict:
        """Start a trial license"""
        trial_key = self.generate_license_key(LicensePlans.TRIAL)
        return self.activate(trial_key)


def get_license_manager() -> LicenseManager:
    return LicenseManager()


def require_module(module: str):
    """Decorator to require module license"""
    from functools import wraps
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            lm = get_license_manager()
            if not lm.is_valid:
                raise LicenseError("License expired or invalid")
            if not lm.is_module_enabled(module):
                raise LicenseError(f"Module '{module}' not included in your license plan")
            return func(*args, **kwargs)
        return wrapper
    return decorator
