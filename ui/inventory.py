"""
Indian SMB ERP - Inventory Module
Product management and stock tracking
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from ui.styles import Theme
from database.models import Product, Inventory, Category, Unit


class InventoryModule(ttk.Frame):
    """Inventory Management Module"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.pack(fill="both", expand=True)
        self.setup_ui()
        self.load_products()

    def setup_ui(self):
        # Action Bar
        action_bar = ttk.Frame(self, padding=10)
        action_bar.pack(fill="x")
        
        ttk.Button(
            action_bar, 
            text="+ Add Product", 
            style="Primary.TButton",
            command=self.show_product_form
        ).pack(side="left", padx=5)
        
        ttk.Button(
            action_bar, 
            text="Stock Adjustment", 
            style="Secondary.TButton",
            command=self.show_stock_form
        ).pack(side="left", padx=5)
        
        # Search
        ttk.Entry(action_bar, width=30).pack(side="right", padx=5)
        ttk.Button(action_bar, text="Search", style="TButton").pack(side="right")
        
        # Product Table
        list_frame = ttk.Frame(self, padding=10)
        list_frame.pack(fill="both", expand=True)
        
        cols = ("Name", "SKU", "HSN", "Category", "Stock", "Unit", "Price", "Status")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings")
        
        column_widths = {
            "Name": 250, "SKU": 100, "HSN": 80, "Category": 120, 
            "Stock": 80, "Unit": 60, "Price": 80, "Status": 80
        }
        
        for col, width in column_widths.items():
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width)
        
        self.tree.pack(fill="both", expand=True)
        
        # Bind double click to edit
        self.tree.bind("<Double-1>", lambda e: self.edit_selected())

    def load_products(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        products = Product.get_all(limit=100)
        for p in products:
            stock = Inventory.get_stock(p['id'])
            
            # Category name logic (todo: join in model)
            cat_name = "General" 
             
            self.tree.insert("", "end", values=(
                p['name'], p['sku'], p['hsn_code'], cat_name, 
                stock, "pcs", f"₹ {p['selling_price']}", 
                "Active" if p['is_active'] else "Inactive"
            ), iid=str(p['id']))

    def show_product_form(self, product_id=None):
        ProductForm(self, product_id)

    def show_stock_form(self):
        StockAdjustmentForm(self)

    def edit_selected(self):
        selected = self.tree.selection()
        if selected:
            self.show_product_form(int(selected[0]))


class ProductForm(tk.Toplevel):
    """Add/Edit Product Window"""
    
    def __init__(self, parent, product_id : Optional[int] = None):
        super().__init__(parent)
        self.parent = parent
        self.product_id = product_id
        self.title("Edit Product" if product_id else "Add New Product")
        
        Theme.center_window(self, 600, 500)
        Theme.apply_theme(self)
        
        self.setup_ui()
        if product_id:
            self.load_data()

    def setup_ui(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Name
        ttk.Label(main_frame, text="Product Name *").pack(anchor="w")
        self.name_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.name_var).pack(fill="x", pady=(0, 10))
        
        # Grid layout for other fields
        grid_frame = ttk.Frame(main_frame)
        grid_frame.pack(fill="x", pady=10)
        
        # Row 1
        ttk.Label(grid_frame, text="SKU").grid(row=0, column=0, sticky="w")
        self.sku_var = tk.StringVar()
        ttk.Entry(grid_frame, textvariable=self.sku_var, width=15).grid(row=1, column=0, padx=5, pady=5)
        
        ttk.Label(grid_frame, text="HSN Code").grid(row=0, column=1, sticky="w")
        self.hsn_var = tk.StringVar()
        ttk.Entry(grid_frame, textvariable=self.hsn_var, width=15).grid(row=1, column=1, padx=5, pady=5)
        
        # Row 2
        ttk.Label(grid_frame, text="Selling Price *").grid(row=2, column=0, sticky="w")
        self.price_var = tk.StringVar()
        ttk.Entry(grid_frame, textvariable=self.price_var, width=15).grid(row=3, column=0, padx=5, pady=5)
        
        ttk.Label(grid_frame, text="GST Rate %").grid(row=2, column=1, sticky="w")
        self.gst_var = tk.StringVar(value="18")
        ttk.Entry(grid_frame, textvariable=self.gst_var, width=15).grid(row=3, column=1, padx=5, pady=5)
        
        # Save Button
        ttk.Button(main_frame, text="Save Product", style="Primary.TButton", command=self.save).pack(pady=20)

    def load_data(self):
        data = Product.get_by_id(self.product_id)
        if data:
            self.name_var.set(data['name'])
            self.sku_var.set(data['sku'] or "")
            self.hsn_var.set(data['hsn_code'] or "")
            self.price_var.set(str(data['selling_price']))
            self.gst_var.set(str(data['gst_rate']))

    def save(self):
        name = self.name_var.get()
        if not name:
            messagebox.showerror("Error", "Name is required")
            return
            
        data = {
            'name': name,
            'sku': self.sku_var.get(),
            'hsn_code': self.hsn_var.get(),
            'selling_price': float(self.price_var.get() or 0),
            'gst_rate': float(self.gst_var.get() or 0)
        }
        
        try:
            if self.product_id:
                Product.update(self.product_id, data)
            else:
                Product.create(data)
            
            messagebox.showinfo("Success", "Product Saved")
            self.parent.load_products()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")


class StockAdjustmentForm(tk.Toplevel):
    """Stock In/Out Form"""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Stock Adjustment")
        Theme.center_window(self, 400, 300)
        Theme.apply_theme(self)
        
        ttk.Label(self, text="Stock Adjustment UI (Coming Soon)", padding=50).pack()
