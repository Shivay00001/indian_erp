"""
Indian SMB ERP - Activation Screen
Strict license enforcement UI
"""
import tkinter as tk
from tkinter import ttk, messagebox
import pyperclip

from ui.styles import Theme
from license.license_manager import get_license_manager, LicenseError
from license.machine_fingerprint import generate_fingerprint

class ActivationWindow(tk.Toplevel):
    """License Activation Dialog"""
    
    def __init__(self, parent, on_success):
        super().__init__(parent)
        self.on_success = on_success
        self.title("Product Activation Required")
        self.resizable(False, False)
        
        # Prevent closing without activation
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        Theme.center_window(self, 500, 600)
        Theme.apply_theme(self)
        
        self.setup_ui()
        
    def setup_ui(self):
        main_frame = ttk.Frame(self, padding=30)
        main_frame.pack(fill="both", expand=True)
        
        # Header
        ttk.Label(
            main_frame, 
            text="License Required", 
            font=Theme.HEADER1, 
            foreground=Theme.DANGER
        ).pack(pady=(0, 10))
        
        ttk.Label(
            main_frame, 
            text="This copy of Indian SMB ERP is not activated.\nPlease contact the administrator to purchase a license.",
            justify="center",
            style="H3.TLabel"
        ).pack(pady=(0, 20))
        
        # Machine ID Section
        id_frame = ttk.LabelFrame(main_frame, text="Your Machine ID", padding=15)
        id_frame.pack(fill="x", pady=10)
        
        self.machine_id = generate_fingerprint()
        
        id_lbl = ttk.Entry(id_frame, font=("Consolas", 10), justify="center")
        id_lbl.insert(0, self.machine_id)
        id_lbl.configure(state="readonly")
        id_lbl.pack(fill="x", pady=(0, 10))
        
        ttk.Button(
            id_frame, 
            text="Copy ID to Clipboard", 
            style="Secondary.TButton",
            command=self.copy_id
        ).pack(fill="x")
        
        ttk.Label(
            id_frame, 
            text="Send this ID to the vendor to receive your key.",
            font=Theme.SMALL,
            foreground=Theme.TEXT_SECONDARY
        ).pack(pady=(10, 0))
        
        # License Key Entry
        input_frame = ttk.LabelFrame(main_frame, text="Enter License Key", padding=15)
        input_frame.pack(fill="x", pady=20)
        
        self.key_var = tk.StringVar()
        entry = ttk.Entry(
            input_frame, 
            textvariable=self.key_var, 
            font=("Consolas", 12), 
            justify="center"
        )
        entry.pack(fill="x", pady=(0, 15))
        entry.focus()
        
        # Action Buttons
        self.btn_activate = ttk.Button(
            input_frame, 
            text="Activate Now", 
            style="Primary.TButton",
            command=self.activate
        )
        self.btn_activate.pack(fill="x")
        
        # Trial Link
        lbl_trial = ttk.Label(
            main_frame, 
            text="Start 30-Day Free Trial", 
            font=Theme.BODY, 
            foreground=Theme.PRIMARY,
            cursor="hand2"
        )
        lbl_trial.pack(pady=20)
        lbl_trial.bind("<Button-1>", lambda e: self.start_trial())

    def copy_id(self):
        pyperclip.copy(self.machine_id)
        messagebox.showinfo("Copied", "Machine ID copied to clipboard!")

    def activate(self):
        key = self.key_var.get().strip()
        if not key:
            messagebox.showerror("Error", "Please enter a license key")
            return
            
        try:
            lm = get_license_manager()
            status = lm.activate(key)
            
            messagebox.showinfo(
                "Success", 
                f"Activation Successful!\n\nPlan: {status['plan_name']}\nExpires in: {status['days_remaining']} days"
            )
            self.destroy()
            self.on_success()
            
        except LicenseError as e:
            messagebox.showerror("Activation Failed", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"System Error: {str(e)}")

    def start_trial(self):
        if messagebox.askyesno("Confirm", "Start 30-day trial? This works only once per machine."):
            try:
                lm = get_license_manager()
                lm.start_trial()
                messagebox.showinfo("Success", "Trial Activated! You have 30 days.")
                self.destroy()
                self.on_success()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def on_close(self):
        if messagebox.askokcancel("Quit", "Application cannot run without activation. Quit?"):
            self.master.destroy()
