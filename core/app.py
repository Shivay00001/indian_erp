"""
Indian SMB ERP - Main Application
Core UI shell, navigation, and module management
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Type
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.styles import Theme
from core.auth import login, AuthenticationError, get_session, logout
from core.permissions import get_accessible_modules, MODULES
from license.license_manager import get_license_manager
from ui.activation import ActivationWindow
from database.db_init import get_database


class LoginWindow(tk.Toplevel):
    """Login Screen"""
    # ... (LoginWindow implementation stays the same) ...
    def __init__(self, parent, on_login_success):
        super().__init__(parent)
        self.title("Indian SMB ERP - Login")
        self.on_login_success = on_login_success
        
        # Configure window
        Theme.center_window(self, 400, 500)
        self.resizable(False, False)
        Theme.apply_theme(self)
        
        # UI Elements
        main_frame = ttk.Frame(self, padding=40)
        main_frame.pack(fill="both", expand=True)

        # Logo/Header
        ttk.Label(main_frame, text="Business ERP", style="Header.TLabel").pack(pady=(0, 10))
        ttk.Label(main_frame, text="Sign in to your account", style="H3.TLabel").pack(pady=(0, 30))
        
        # Username
        ttk.Label(main_frame, text="Username").pack(anchor="w", pady=(0, 5))
        self.username_var = tk.StringVar()
        entry_user = ttk.Entry(main_frame, textvariable=self.username_var, font=Theme.BODY)
        entry_user.pack(fill="x", pady=(0, 15))
        entry_user.focus()
        
        # Password
        ttk.Label(main_frame, text="Password").pack(anchor="w", pady=(0, 5))
        self.password_var = tk.StringVar()
        entry_pass = ttk.Entry(main_frame, textvariable=self.password_var, show="•", font=Theme.BODY)
        entry_pass.pack(fill="x", pady=(0, 20))
        
        # Error Message
        self.error_label = ttk.Label(main_frame, text="", style="Error.TLabel", wraplength=300)
        self.error_label.pack(pady=(0, 15))
        
        # Login Button
        btn_login = ttk.Button(
            main_frame, 
            text="Sign In", 
            style="Primary.TButton", 
            command=self.perform_login
        )
        btn_login.pack(fill="x", pady=(0, 10))
        
        # Bind enter key
        self.bind('<Return>', lambda e: self.perform_login())
        
        # Default admin hint
        ttk.Label(main_frame, text="Default: admin / admin123", style="Error.TLabel").pack(pady=20)

    def perform_login(self):
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        
        if not username or not password:
            self.error_label.config(text="Please enter both username and password")
            return
            
        try:
            user = login(username, password)
            self.destroy()
            self.on_login_success(user)
        except AuthenticationError as e:
            self.error_label.config(text=str(e))
        except Exception as e:
            self.error_label.config(text=f"System error: {str(e)}")


class ERPApplication(tk.Tk):
    """Main Application Shell"""
    
    def __init__(self):
        super().__init__()
        
        self.title("Indian SMB ERP - Enterprise Edition")
        self.state('zoomed')  # Maximize
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Initialize Theme
        Theme.apply_theme(self)
        
        # Session state
        self.current_user = None
        self.active_module = None
        self.module_frames: Dict[str, ttk.Frame] = {}
        
        # UI Layout
        self.setup_layout()
        self.withdraw() # Hide main window
        
        # Check License First
        self.check_license()

    def check_license(self):
        """Verify license before showing login"""
        lm = get_license_manager()
        
        # Helper to run revocation check in background (fail open for UX speed)
        # For strict security, this should be awaited, but for UX we might fire-and-forget 
        # or show a splash. Here we do a synchronous check with short timeout.
        # In production, replace with your actual raw gist/json URL
        REVOCATION_URL = "https://example.com/api/revoked_licenses.json" 
        try:
            if lm.is_valid:
                lm.check_remote_revocation(REVOCATION_URL)
        except:
            pass
            
        if lm.is_valid:
            self.show_login()
        else:
            self.show_activation()

    def show_activation(self):
        """Show activation window"""
        ActivationWindow(self, self.on_activation_success)

    def on_activation_success(self):
        """Called when activation completes successfully"""
        self.show_login()

    def setup_layout(self):
        """Create the main sidebar and content area layout"""
        self.main_container = ttk.Frame(self)
        self.main_container.pack(fill="both", expand=True)
        
        # Sidebar
        self.sidebar = ttk.Frame(self.main_container, style="Sidebar.TFrame", width=250)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        
        # Header (Top Bar)
        self.header = ttk.Frame(self.main_container, height=60, style="Card.TFrame")
        self.header.pack(side="top", fill="x")
        self.header.pack_propagate(False)
        
        # Content Area
        self.content_area = ttk.Frame(self.main_container, padding=20)
        self.content_area.pack(side="right", fill="both", expand=True)
        
        # Header Content
        self.header_label = ttk.Label(self.header, text="Dashboard", style="SubHeader.TLabel")
        self.header_label.pack(side="left", padx=20, pady=15)
        
        self.user_label = ttk.Label(self.header, text="", style="H3.TLabel")
        self.user_label.pack(side="right", padx=20)
        
        # Sidebar Content creates
        self.create_sidebar_items()

    def create_sidebar_items(self):
        """Create sidebar navigation based on permissions"""
        # Clear existing
        for widget in self.sidebar.winfo_children():
            widget.destroy()
            
        # App Title in Sidebar
        title_frame = ttk.Frame(self.sidebar, style="Sidebar.TFrame", height=80)
        title_frame.pack(fill="x", pady=(0, 20))
        ttk.Label(
            title_frame, 
            text="SMB ERP", 
            font=Theme.HEADER2, 
            background=Theme.BG_SIDEBAR, 
            foreground=Theme.TEXT_WHITE
        ).pack(pady=20)
        
        # Navigation Items
        if self.current_user:
            modules = get_accessible_modules()
            
            # Define icons (unicode placeholders for now)
            icons = {
                'dashboard': '📊',
                'billing': '💰',
                'inventory': '📦',
                'customers': '👥',
                'vendors': '🏢',
                'accounts': '📔',
                'reports': '📑',
                'settings': '⚙️',
                'users': '👤'
            }
            
            for mod_key in modules:
                mod_name = MODULES.get(mod_key, mod_key.title())
                icon = icons.get(mod_key, '•')
                
                btn = ttk.Button(
                    self.sidebar,
                    text=f"  {icon}  {mod_name}",
                    style="Sidebar.TButton",
                    command=lambda m=mod_key: self.load_module(m)
                )
                btn.pack(fill="x", pady=2)
            
            # Logout at bottom
            ttk.Frame(self.sidebar, style="Sidebar.TFrame").pack(fill="both", expand=True) # Spacer
            
            ttk.Button(
                self.sidebar,
                text="  🚪  Logout",
                style="Sidebar.TButton",
                command=self.logout
            ).pack(fill="x", pady=20)

    def show_login(self):
        """Show login dialog"""
        LoginWindow(self, self.on_login_success)

    def on_login_success(self, user):
        """Handle successful login"""
        self.current_user = user
        self.user_label.config(text=f"{user['full_name']} ({user['role_name']})")
        self.deiconify()  # Show main window
        self.create_sidebar_items()
        
        # Load default module (Dashboard)
        self.load_module('dashboard')

    def load_module(self, module_name):
        """Load a specific module into the content area"""
        if self.active_module == module_name:
            return
            
        # Clear content area
        for widget in self.content_area.winfo_children():
            widget.destroy()
            
        self.header_label.config(text=MODULES.get(module_name, module_name.title()))
        self.active_module = module_name
        
        try:
            if module_name == 'dashboard':
                self.show_dashboard()
            elif module_name == 'billing':
                from ui.billing import BillingModule
                BillingModule(self.content_area)
            elif module_name == 'inventory':
                from ui.inventory import InventoryModule
                InventoryModule(self.content_area)
            elif module_name == 'settings':
                from ui.settings import SettingsModule
                SettingsModule(self.content_area)
            else:
                self.show_placeholder(module_name)
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to load module {module_name}: {str(e)}")

    def show_dashboard(self):
        """Show the dashboard module"""
        # Placeholder for dashboard content until implemented
        ttk.Label(self.content_area, text="Executive Dashboard", style="Header.TLabel").pack(anchor="w", pady=20)
        
        # KPI Cards Row
        kpi_frame = ttk.Frame(self.content_area)
        kpi_frame.pack(fill="x", pady=20)
        
        kpis = [
            ("Today's Sales", "₹ 24,500"),
            ("Pending Invoices", "12"),
            ("Low Stock Items", "5"),
            ("Active Customers", "148")
        ]
        
        for title, value in kpis:
            card = ttk.Frame(kpi_frame, style="Card.TFrame", padding=20)
            card.pack(side="left", fill="both", expand=True, padx=10)
            
            ttk.Label(card, text=title, style="H3.TLabel").pack(anchor="w")
            ttk.Label(card, text=value, style="Header.TLabel", foreground=Theme.PRIMARY).pack(anchor="w", pady=(10, 0))

    def show_placeholder(self, module_name):
        """Show placeholder for unimplemented modules"""
        ttk.Label(
            self.content_area, 
            text=f"{MODULES.get(module_name, module_name)} Module", 
            style="Header.TLabel"
        ).pack(pady=50)
        ttk.Label(
            self.content_area, 
            text="Coming Soon in Phase 2", 
            style="H3.TLabel"
        ).pack()

    def logout(self):
        """Handle logout"""
        if messagebox.askyesno("Confirm Logout", "Are you sure you want to logout?"):
            logout()
            self.current_user = None
            self.withdraw()
            self.show_login()

    def on_close(self):
        """Handle app closing"""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            try:
                # Auto-backup on exit
                db = get_database()
                db.auto_backup(user_id=self.current_user['id'] if self.current_user else None)
            except Exception as e:
                print(f"Auto-backup warning: {e}")
            self.destroy()


if __name__ == "__main__":
    app = ERPApplication()
    app.mainloop()
