"""
Indian SMB ERP - Authentication System
User login, session management, password hashing
"""
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict
from database.models import User, AuditLog


class AuthenticationError(Exception):
    """Authentication related errors"""
    pass


class Session:
    """Current user session"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.user = None
            cls._instance.role_id = None
            cls._instance.role_name = None
            cls._instance.login_time = None
        return cls._instance
    
    @property
    def is_authenticated(self) -> bool:
        return self.user is not None
    
    @property
    def user_id(self) -> Optional[int]:
        return self.user['id'] if self.user else None
    
    def clear(self):
        self.user = None
        self.role_id = None
        self.role_name = None
        self.login_time = None


def get_session() -> Session:
    return Session()


def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def login(username: str, password: str) -> Dict:
    """
    Authenticate user and create session
    Returns: User dict on success
    Raises: AuthenticationError on failure
    """
    user = User.get_by_username(username)
    
    if not user:
        AuditLog.log(None, 'LOGIN_FAILED', 'auth', new_values={'username': username, 'reason': 'user_not_found'})
        raise AuthenticationError("Invalid username or password")
    
    if not user.get('is_active', True):
        AuditLog.log(user['id'], 'LOGIN_FAILED', 'auth', new_values={'reason': 'account_disabled'})
        raise AuthenticationError("Account is disabled. Contact administrator.")
    
    if not verify_password(password, user['password_hash']):
        AuditLog.log(user['id'], 'LOGIN_FAILED', 'auth', new_values={'reason': 'invalid_password'})
        raise AuthenticationError("Invalid username or password")
    
    # Create session
    session = get_session()
    session.user = user
    session.role_id = user['role_id']
    session.role_name = user.get('role_name', 'Unknown')
    session.login_time = datetime.now()
    
    # Update last login
    User.update_last_login(user['id'])
    
    # Audit log
    AuditLog.log(user['id'], 'LOGIN_SUCCESS', 'auth')
    
    return user


def logout():
    """Clear current session"""
    session = get_session()
    if session.is_authenticated:
        AuditLog.log(session.user_id, 'LOGOUT', 'auth')
    session.clear()


def change_password(user_id: int, old_password: str, new_password: str) -> bool:
    """
    Change user password
    Returns: True on success
    Raises: AuthenticationError on failure
    """
    user = User.get_by_id(user_id)
    
    if not user:
        raise AuthenticationError("User not found")
    
    if not verify_password(old_password, user['password_hash']):
        raise AuthenticationError("Current password is incorrect")
    
    if len(new_password) < 6:
        raise AuthenticationError("New password must be at least 6 characters")
    
    new_hash = hash_password(new_password)
    User.update(user_id, {'password_hash': new_hash})
    
    AuditLog.log(user_id, 'PASSWORD_CHANGED', 'auth')
    
    return True


def create_user(username: str, password: str, full_name: str, role_id: int, 
                email: str = None, phone: str = None, created_by: int = None) -> int:
    """
    Create a new user
    Returns: New user ID
    Raises: AuthenticationError on failure
    """
    # Check if username exists
    if User.get_by_username(username):
        raise AuthenticationError(f"Username '{username}' already exists")
    
    if len(password) < 6:
        raise AuthenticationError("Password must be at least 6 characters")
    
    user_data = {
        'username': username,
        'password_hash': hash_password(password),
        'full_name': full_name,
        'role_id': role_id,
        'email': email,
        'phone': phone,
        'is_active': True,
        'created_at': datetime.now().isoformat()
    }
    
    user_id = User.create(user_data)
    
    AuditLog.log(created_by, 'USER_CREATED', 'users', user_id, new_values={'username': username, 'role_id': role_id})
    
    return user_id


def reset_password(user_id: int, new_password: str, reset_by: int = None) -> bool:
    """Reset user password (admin function)"""
    if len(new_password) < 6:
        raise AuthenticationError("Password must be at least 6 characters")
    
    new_hash = hash_password(new_password)
    User.update(user_id, {'password_hash': new_hash})
    
    AuditLog.log(reset_by, 'PASSWORD_RESET', 'users', user_id)
    
    return True


def toggle_user_status(user_id: int, toggled_by: int = None) -> bool:
    """Enable/disable user account"""
    user = User.get_by_id(user_id)
    if not user:
        raise AuthenticationError("User not found")
    
    new_status = not user.get('is_active', True)
    User.update(user_id, {'is_active': new_status})
    
    action = 'USER_ENABLED' if new_status else 'USER_DISABLED'
    AuditLog.log(toggled_by, action, 'users', user_id)
    
    return new_status


def require_auth(func):
    """Decorator to require authentication"""
    def wrapper(*args, **kwargs):
        if not get_session().is_authenticated:
            raise AuthenticationError("Authentication required")
        return func(*args, **kwargs)
    return wrapper
