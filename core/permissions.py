"""
Indian SMB ERP - Permissions System
Role-based access control for modules and actions
"""
from functools import wraps
from typing import List, Dict, Optional
from database.models import Permission, Role
from core.auth import get_session, AuthenticationError


class PermissionError(Exception):
    """Permission denied error"""
    pass


# Module definitions
MODULES = {
    'dashboard': 'Dashboard',
    'billing': 'Billing & Invoices',
    'inventory': 'Inventory Management',
    'customers': 'Customer Management',
    'vendors': 'Vendor Management',
    'accounts': 'Accounts & Payments',
    'reports': 'Reports & Analytics',
    'settings': 'Settings & Configuration',
    'users': 'User Management'
}

# Actions
ACTIONS = ['can_view', 'can_create', 'can_edit', 'can_delete', 'can_export']


def check_permission(module: str, action: str = 'can_view') -> bool:
    """Check if current user has permission for module action"""
    session = get_session()
    if not session.is_authenticated:
        return False
    
    # Admin has all permissions
    if session.role_name == 'Admin':
        return True
    
    return Permission.check_permission(session.role_id, module, action)


def get_user_permissions(role_id: int = None) -> Dict[str, Dict[str, bool]]:
    """Get all permissions for a role"""
    if role_id is None:
        session = get_session()
        if not session.is_authenticated:
            return {}
        role_id = session.role_id
    
    permissions = Permission.get_by_role(role_id)
    result = {}
    for perm in permissions:
        result[perm['module']] = {
            'can_view': bool(perm['can_view']),
            'can_create': bool(perm['can_create']),
            'can_edit': bool(perm['can_edit']),
            'can_delete': bool(perm['can_delete']),
            'can_export': bool(perm['can_export'])
        }
    return result


def get_accessible_modules() -> List[str]:
    """Get list of modules the current user can access"""
    session = get_session()
    if not session.is_authenticated:
        return []
    
    if session.role_name == 'Admin':
        return list(MODULES.keys())
    
    permissions = get_user_permissions()
    return [mod for mod, perms in permissions.items() if perms.get('can_view', False)]


def require_permission(module: str, action: str = 'can_view'):
    """Decorator to require specific permission"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            session = get_session()
            if not session.is_authenticated:
                raise AuthenticationError("Authentication required")
            if not check_permission(module, action):
                raise PermissionError(f"Permission denied: {action} on {module}")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def setup_role_permissions(role_id: int, permissions: Dict[str, Dict[str, bool]]):
    """Set up permissions for a role"""
    from database.db_init import get_database
    db = get_database()
    cursor = db.get_cursor()
    
    for module, perms in permissions.items():
        cursor.execute("""
            INSERT OR REPLACE INTO permissions 
            (role_id, module, can_view, can_create, can_edit, can_delete, can_export)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            role_id, module,
            perms.get('can_view', False),
            perms.get('can_create', False),
            perms.get('can_edit', False),
            perms.get('can_delete', False),
            perms.get('can_export', False)
        ))
    
    db.commit()


# Default permission templates
DEFAULT_PERMISSIONS = {
    'Manager': {
        'dashboard': {'can_view': True, 'can_create': False, 'can_edit': False, 'can_delete': False, 'can_export': True},
        'billing': {'can_view': True, 'can_create': True, 'can_edit': True, 'can_delete': False, 'can_export': True},
        'inventory': {'can_view': True, 'can_create': True, 'can_edit': True, 'can_delete': False, 'can_export': True},
        'customers': {'can_view': True, 'can_create': True, 'can_edit': True, 'can_delete': False, 'can_export': True},
        'vendors': {'can_view': True, 'can_create': True, 'can_edit': True, 'can_delete': False, 'can_export': True},
        'accounts': {'can_view': True, 'can_create': True, 'can_edit': True, 'can_delete': False, 'can_export': True},
        'reports': {'can_view': True, 'can_create': False, 'can_edit': False, 'can_delete': False, 'can_export': True},
        'settings': {'can_view': True, 'can_create': False, 'can_edit': False, 'can_delete': False, 'can_export': False},
    },
    'Accountant': {
        'dashboard': {'can_view': True, 'can_create': False, 'can_edit': False, 'can_delete': False, 'can_export': True},
        'billing': {'can_view': True, 'can_create': True, 'can_edit': True, 'can_delete': False, 'can_export': True},
        'accounts': {'can_view': True, 'can_create': True, 'can_edit': True, 'can_delete': False, 'can_export': True},
        'reports': {'can_view': True, 'can_create': False, 'can_edit': False, 'can_delete': False, 'can_export': True},
        'customers': {'can_view': True, 'can_create': False, 'can_edit': False, 'can_delete': False, 'can_export': True},
        'vendors': {'can_view': True, 'can_create': False, 'can_edit': False, 'can_delete': False, 'can_export': True},
    },
    'Sales': {
        'dashboard': {'can_view': True, 'can_create': False, 'can_edit': False, 'can_delete': False, 'can_export': False},
        'billing': {'can_view': True, 'can_create': True, 'can_edit': False, 'can_delete': False, 'can_export': True},
        'customers': {'can_view': True, 'can_create': True, 'can_edit': True, 'can_delete': False, 'can_export': True},
        'inventory': {'can_view': True, 'can_create': False, 'can_edit': False, 'can_delete': False, 'can_export': False},
    },
    'Inventory': {
        'dashboard': {'can_view': True, 'can_create': False, 'can_edit': False, 'can_delete': False, 'can_export': False},
        'inventory': {'can_view': True, 'can_create': True, 'can_edit': True, 'can_delete': False, 'can_export': True},
        'vendors': {'can_view': True, 'can_create': True, 'can_edit': True, 'can_delete': False, 'can_export': True},
    }
}


def initialize_default_permissions():
    """Initialize default permissions for all roles"""
    from database.db_init import get_database
    db = get_database()
    cursor = db.get_cursor()
    
    for role_name, permissions in DEFAULT_PERMISSIONS.items():
        cursor.execute("SELECT id FROM roles WHERE name = ?", (role_name,))
        role = cursor.fetchone()
        if role:
            setup_role_permissions(role['id'], permissions)
