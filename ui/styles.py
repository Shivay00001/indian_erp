"""
Indian SMB ERP - UI Styles
Centralized theme configuration for modern customized Tkinter implementation
"""
from tkinter import ttk
import tkinter as tk
from typing import Dict

# Check if sv_ttk is installed (optional modern theme)
try:
    import sv_ttk
    HAS_SV_TTK = True
except ImportError:
    HAS_SV_TTK = False


class Theme:
    """Premium Enterprise Theme Configuration"""
    
    # Premium Color Palette
    PRIMARY = "#2563EB"       # Royal Blue
    PRIMARY_DARK = "#1E40AF"
    SECONDARY = "#64748B"     # Slate
    SUCCESS = "#059669"       # Emerald
    DANGER = "#DC2626"        # Red
    WARNING = "#D97706"       # Amber
    
    # Backgrounds
    BG_MAIN = "#F8FAFC"       # Slate-50
    BG_SIDEBAR = "#0F172A"    # Slate-900
    BG_HEADER = "#FFFFFF"
    BG_CARD = "#FFFFFF"
    
    # Text
    TEXT_PRIMARY = "#1E293B"  # Slate-800
    TEXT_SECONDARY = "#64748B"
    TEXT_WHITE = "#FFFFFF"
    TEXT_MUTED = "#94A3B8"
    
    # Borders
    BORDER_LIGHT = "#E2E8F0"
    
    # Fonts - Modern Stack
    FONT_FAMILY = "Segoe UI"
    HEADER1 = (FONT_FAMILY, 24, "bold")
    HEADER2 = (FONT_FAMILY, 18, "bold")
    HEADER3 = (FONT_FAMILY, 14, "bold")
    BODY = (FONT_FAMILY, 10)
    BODY_BOLD = (FONT_FAMILY, 10, "bold")
    SMALL = (FONT_FAMILY, 9)
    
    @classmethod
    def apply_theme(cls, root: tk.Tk):
        """Apply the global premium theme"""
        
        # Configure basics
        root.option_add("*Font", cls.BODY)
        root.configure(bg=cls.BG_MAIN)
        
        style = ttk.Style()
        style.theme_use('clam')
        
        # === Base Configuration ===
        style.configure(".", background=cls.BG_MAIN, foreground=cls.TEXT_PRIMARY, font=cls.BODY)
        
        # === Buttons ===
        # Primary Action Button
        style.configure(
            "Primary.TButton",
            background=cls.PRIMARY,
            foreground=cls.TEXT_WHITE,
            font=cls.BODY_BOLD,
            padding=(20, 10),
            borderwidth=0,
            relief="flat"
        )
        style.map(
            "Primary.TButton",
            background=[("active", cls.PRIMARY_DARK), ("pressed", cls.PRIMARY_DARK)]
        )
        
        # Secondary Button
        style.configure(
            "Secondary.TButton",
            background=cls.BG_MAIN,
            foreground=cls.TEXT_SECONDARY,
            font=cls.BODY,
            padding=(15, 8),
            borderwidth=1,
            relief="solid",
            bordercolor=cls.BORDER_LIGHT
        )
        style.map(
            "Secondary.TButton",
            background=[("active", cls.BG_HEADER)],
            foreground=[("active", cls.PRIMARY)]
        )
        
        # Danger Button
        style.configure(
            "Danger.TButton",
            background=cls.DANGER,
            foreground=cls.TEXT_WHITE,
            font=cls.BODY_BOLD,
            padding=(15, 8),
            borderwidth=0
        )
        
        # === Sidebar ===
        style.configure("Sidebar.TFrame", background=cls.BG_SIDEBAR)
        
        style.configure(
            "Sidebar.TButton",
            background=cls.BG_SIDEBAR,
            foreground="#94A3B8",  # Muted Text
            font=(cls.FONT_FAMILY, 11),
            anchor="w",
            padding=(25, 12),
            borderwidth=0
        )
        style.map(
            "Sidebar.TButton",
            background=[("active", "#1E293B"), ("selected", cls.PRIMARY)], # Darker slate on hover, Blue on selected
            foreground=[("active", cls.TEXT_WHITE), ("selected", cls.TEXT_WHITE)]
        )
        
        # === Cards & Panels ===
        style.configure(
            "Card.TFrame",
            background=cls.BG_CARD,
            relief="flat",
            borderwidth=1,
            bordercolor=cls.BORDER_LIGHT
        )
        
        # === Treeview (Modern Data Table) ===
        style.configure(
            "Treeview",
            background=cls.BG_CARD,
            fieldbackground=cls.BG_CARD,
            foreground=cls.TEXT_PRIMARY,
            rowheight=35,
            font=cls.BODY,
            borderwidth=0
        )
        style.configure(
            "Treeview.Heading",
            background=cls.BG_MAIN,
            foreground=cls.TEXT_SECONDARY,
            font=(cls.FONT_FAMILY, 9, "bold"),
            relief="flat",
            padding=(10, 10)
        )
        style.map("Treeview", background=[("selected", cls.PRIMARY_DARK)])
        
        # === Inputs ===
        style.configure(
            "TEntry",
            padding=8,
            relief="flat",
            borderwidth=1,
            fieldbackground=cls.BG_HEADER,
            bordercolor=cls.BORDER_LIGHT
        )
        
        # === Typography Styles ===
        style.configure("Header.TLabel", font=cls.HEADER1, background=cls.BG_MAIN, foreground=cls.TEXT_PRIMARY)
        style.configure("SubHeader.TLabel", font=cls.HEADER2, background=cls.BG_MAIN, foreground=cls.TEXT_PRIMARY)
        style.configure("H3.TLabel", font=cls.HEADER3, background=cls.BG_CARD, foreground=cls.TEXT_SECONDARY)
        style.configure("Error.TLabel", foreground=cls.DANGER, font=cls.SMALL, background=cls.BG_MAIN)
        
        # Fix container backgrounds
        style.configure("TFrame", background=cls.BG_MAIN)
        style.configure("TLabelframe", background=cls.BG_MAIN, bordercolor=cls.BORDER_LIGHT)
        style.configure("TLabelframe.Label", background=cls.BG_MAIN, foreground=cls.TEXT_SECONDARY, font=cls.BODY_BOLD)

    @staticmethod
    def center_window(window: tk.Toplevel, width: int = 800, height: int = 600):
        """Center a window on the screen"""
        window.update_idletasks()
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        
        window.geometry(f"{width}x{height}+{x}+{y}")
