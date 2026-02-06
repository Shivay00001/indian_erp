"""
Indian SMB ERP - Billing Module
Invoice generation, GST calculations, and sales history
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime
from typing import Dict, List, Optional
from decimal import Decimal

from ui.styles import Theme
from database.models import Invoice, Customer, Product, InvoiceItem, CompanySettings
from utils.validators import calculate_gst
from core.permissions import require_permission, check_permission


class BillingModule(ttk.Frame):
    """Billing and Invoice Management Module"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.pack(fill="both", expand=True)
        
        # State
        self.cart_items = []
        self.selected_customer = None
        self.is_igst = False
        
        # Load settings
        self.settings = CompanySettings.get_settings()
        
        # UI Layout
        self.setup_ui()
        
        # Initial Load
        self.load_invoices()

    def setup_ui(self):
        """Create the UI layout"""
        # Top Bar (Actions)
        action_bar = ttk.Frame(self, padding=10)
        action_bar.pack(fill="x")
        
        ttk.Button(
            action_bar, 
            text="+ New Invoice", 
            style="Primary.TButton",
            command=self.show_new_invoice_form
        ).pack(side="left")
        
        ttk.Entry(action_bar, width=30).pack(side="right", padx=5)
        ttk.Button(action_bar, text="Search", style="TButton").pack(side="right")
        
        # Invoices List (Treeview)
        list_frame = ttk.Frame(self, padding=10)
        list_frame.pack(fill="both", expand=True)
        
        cols = ("No", "Date", "Customer", "Amount", "Status", "Payment")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings", selectmode="browse")
        
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)
        
        self.tree.column("Customer", width=200)
        self.tree.pack(fill="both", expand=True)
        
        # Context Menu
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="View/Print", command=self.view_selected_invoice)
        self.context_menu.add_command(label="Cancel Invoice", command=self.cancel_selected_invoice)
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<Double-1>", lambda e: self.view_selected_invoice())

    def load_invoices(self):
        """Load invoices into treeview"""
        # Clear existing
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        invoices = Invoice.get_all(limit=50) # Pagination todo
        
        for inv in invoices:
            customer = Customer.get_by_id(inv['customer_id'])
            cust_name = customer['name'] if customer else "Unknown"
            
            self.tree.insert("", "end", values=(
                inv['invoice_number'],
                inv['invoice_date'],
                cust_name,
                f"₹ {inv['total_amount']}",
                inv['status'].title(),
                inv['payment_status'].title()
            ), iid=str(inv['id']))

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def show_new_invoice_form(self):
        """Open new invoice creation window"""
        InvoiceForm(self)

    def view_selected_invoice(self):
        selected = self.tree.selection()
        if not selected:
            return
        
        invoice_id = int(selected[0])
        # todo: Show viewer
        messagebox.showinfo("Info", f"Viewing invoice {invoice_id}")

    def cancel_selected_invoice(self):
        selected = self.tree.selection()
        if not selected:
            return
            
        if messagebox.askyesno("Confirm", "Cancel this invoice? Stock will be restored."):
            # todo: cancel logic
            pass


class InvoiceForm(tk.Toplevel):
    """New Invoice Creation Window"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.title("New Sales Invoice")
        self.state('zoomed')
        Theme.apply_theme(self)
        
        self.parent = parent
        self.cart = []
        self.customer = None
        
        self.setup_ui()
        self.generate_invoice_number()

    def setup_ui(self):
        """Create the invoice form layout"""
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # === Header Section: Customer & Invoice Details ===
        header_frame = ttk.LabelFrame(main_frame, text="Invoice Details", padding=10)
        header_frame.pack(fill="x", pady=(0, 20))
        
        # Row 1: Customer Search | Date | Invoice #
        row1 = ttk.Frame(header_frame)
        row1.pack(fill="x")
        
        # Customer Search
        ttk.Label(row1, text="Customer:").pack(side="left")
        self.cust_var = tk.StringVar()
        self.cust_entry = ttk.Entry(row1, textvariable=self.cust_var, width=30)
        self.cust_entry.pack(side="left", padx=5)
        self.cust_entry.bind('<KeyRelease>', self.search_customer)
        
        # Date
        ttk.Label(row1, text="Date:").pack(side="left", padx=(20, 5))
        self.date_var = tk.StringVar(value=date.today().strftime('%Y-%m-%d'))
        ttk.Entry(row1, textvariable=self.date_var, width=12).pack(side="left")
        
        # Invoice No
        ttk.Label(row1, text="Invoice #:").pack(side="left", padx=(20, 5))
        self.inv_no_label = ttk.Label(row1, text="Auto-Generated", font=Theme.BODY_BOLD)
        self.inv_no_label.pack(side="left")
        
        # GST Type
        self.gst_type_var = tk.StringVar(value="Intra-State (CGST+SGST)")
        ttk.OptionMenu(row1, self.gst_type_var, "Intra-State (CGST+SGST)", "Intra-State (CGST+SGST)", "Inter-State (IGST)").pack(side="right")
        
        # Customer Info Label
        self.cust_info_label = ttk.Label(header_frame, text="No customer selected", foreground=Theme.TEXT_SECONDARY)
        self.cust_info_label.pack(anchor="w", pady=(5, 0))
        
        # === Item Entry Section ===
        item_frame = ttk.LabelFrame(main_frame, text="Add Items", padding=10)
        item_frame.pack(fill="x", pady=(0, 20))
        
        # Product Search
        ttk.Label(item_frame, text="Product").grid(row=0, column=0, padx=5)
        self.prod_var = tk.StringVar()
        self.prod_entry = ttk.Entry(item_frame, textvariable=self.prod_var, width=30)
        self.prod_entry.grid(row=1, column=0, padx=5)
        self.prod_entry.bind('<KeyRelease>', self.search_product)
        self.prod_entry.bind('<Return>', lambda e: self.item_qty.focus())
        
        # Qty
        ttk.Label(item_frame, text="Qty").grid(row=0, column=1, padx=5)
        self.item_qty = ttk.Entry(item_frame, width=8)
        self.item_qty.grid(row=1, column=1, padx=5)
        
        # Rate
        ttk.Label(item_frame, text="Rate").grid(row=0, column=2, padx=5)
        self.item_rate = ttk.Entry(item_frame, width=10)
        self.item_rate.grid(row=1, column=2, padx=5)
        
        # Discount
        ttk.Label(item_frame, text="Disc %").grid(row=0, column=3, padx=5)
        self.item_disc = ttk.Entry(item_frame, width=6)
        self.item_disc.insert(0, "0")
        self.item_disc.grid(row=1, column=3, padx=5)
        
        # GST %
        ttk.Label(item_frame, text="GST %").grid(row=0, column=4, padx=5)
        self.item_gst = ttk.Entry(item_frame, width=6)
        self.item_gst.insert(0, "18")
        self.item_gst.grid(row=1, column=4, padx=5)
        
        # Add Button
        ttk.Button(item_frame, text="Add Item", command=self.add_item, style="Primary.TButton").grid(row=1, column=5, padx=10)
        
        # === Items Table ===
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill="both", expand=True)
        
        cols = ("Product", "HSN", "Qty", "Rate", "Disc", "Taxable", "GST", "Total")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        for col in cols:
            self.tree.heading(col, text=col)
            if col == "Product":
                self.tree.column(col, width=250)
            else:
                self.tree.column(col, width=80)
                
        self.tree.pack(side="left", fill="both", expand=True)
        
        # Scrollbar
        sb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sb.set)
        
        # Delete item binding
        self.tree.bind("<Delete>", self.remove_selected_item)
        
        # === Footer: Totals & Actions ===
        footer_frame = ttk.Frame(main_frame, padding=(0, 20))
        footer_frame.pack(fill="x")
        
        # Totals Panel (Right aligned)
        total_panel = ttk.Frame(footer_frame, style="Card.TFrame", padding=15)
        total_panel.pack(side="right")
        
        self.lbl_subtotal = self.create_total_row(total_panel, "Subtotal:", "0.00", 0)
        self.lbl_cgst = self.create_total_row(total_panel, "CGST:", "0.00", 1)
        self.lbl_sgst = self.create_total_row(total_panel, "SGST:", "0.00", 2)
        self.lbl_igst = self.create_total_row(total_panel, "IGST:", "0.00", 3)
        self.lbl_round = self.create_total_row(total_panel, "Round Off:", "0.00", 4)
        
        ttk.Separator(total_panel, orient="horizontal").grid(row=5, column=0, columnspan=2, sticky="ew", pady=5)
        
        ttk.Label(total_panel, text="Grand Total:", font=Theme.HEADER2).grid(row=6, column=0, sticky="e")
        self.lbl_grand_total = ttk.Label(total_panel, text="₹ 0.00", font=Theme.HEADER2, foreground=Theme.PRIMARY)
        self.lbl_grand_total.grid(row=6, column=1, sticky="e", padx=10)
        
        # Action Buttons (Left aligned)
        btn_frame = ttk.Frame(footer_frame)
        btn_frame.pack(side="left", anchor="s")
        
        ttk.Button(btn_frame, text="Save & Print", style="Primary.TButton", command=self.save_invoice).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Save Only", style="Secondary.TButton", command=lambda: self.save_invoice(print_it=False)).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", style="Danger.TButton", command=self.destroy).pack(side="left", padx=5)

    def create_total_row(self, parent, label, value, row):
        ttk.Label(parent, text=label, font=Theme.BODY).grid(row=row, column=0, sticky="e", pady=2)
        lbl = ttk.Label(parent, text=value, font=Theme.BODY_BOLD)
        lbl.grid(row=row, column=1, sticky="e", padx=10, pady=2)
        return lbl

    def search_customer(self, event=None):
        query = self.cust_var.get()
        if len(query) < 3: return
        # todo: implement autocomplete popup
        # For now simple search
        custs = Customer.search(query)
        if custs:
            self.customer = custs[0] # Auto-select first for now logic
            self.cust_info_label.config(text=f"Selected: {self.customer['name']} | GST: {self.customer.get('gstin','N/A')}")
            
            # Check state for Interstate
            # self.gst_type_var.set(...) logic here

    def search_product(self, event=None):
        query = self.prod_var.get()
        if len(query) < 2: return
        # todo: implement autocomplete popup
        
    def generate_invoice_number(self):
        new_no = Invoice.get_next_number('SALES')
        self.inv_no_label.config(text=new_no)

    def add_item(self):
        # Placeholder add logic
        product_name = self.prod_var.get()
        if not product_name: 
            messagebox.showerror("Error", "Select a product")
            return
            
        try:
            qty = float(self.item_qty.get())
            rate = float(self.item_rate.get())
            disc = float(self.item_disc.get())
            gst_rate = float(self.item_gst.get())
            
            # Calculate item totals
            amount = qty * rate
            disc_amt = amount * (disc / 100)
            taxable = amount - disc_amt
            
            is_igst = "Inter-State" in self.gst_type_var.get()
            tax = calculate_gst(taxable, gst_rate, is_igst)
            
            total = taxable + tax['total_gst']
            
            item = {
                'product': product_name,
                'hsn': '1234', # Dummy
                'qty': qty,
                'rate': rate,
                'disc': disc,
                'taxable': taxable,
                'gst_rate': gst_rate,
                'gst_amt': tax['total_gst'],
                'total': total,
                'tax_details': tax
            }
            
            self.cart.append(item)
            self.tree.insert("", "end", values=(
                product_name, '1234', qty, rate, f"{disc}%", 
                f"{taxable:.2f}", f"{tax['total_gst']:.2f}", f"{total:.2f}"
            ))
            
            self.calculate_totals()
            
            # Clear inputs
            self.prod_var.set("")
            self.item_qty.delete(0, 'end')
            self.prod_entry.focus()
            
        except ValueError:
            messagebox.showerror("Error", "Invalid numeric values")

    def remove_selected_item(self, event):
        selected = self.tree.selection()
        if selected:
            idx = self.tree.index(selected[0])
            self.cart.pop(idx)
            self.tree.delete(selected[0])
            self.calculate_totals()

    def calculate_totals(self):
        subtotal = sum(i['taxable'] for i in self.cart)
        total_cgst = sum(i['tax_details']['cgst_amount'] for i in self.cart)
        total_sgst = sum(i['tax_details']['sgst_amount'] for i in self.cart)
        total_igst = sum(i['tax_details']['igst_amount'] for i in self.cart)
        
        grand_total = subtotal + total_cgst + total_sgst + total_igst
        round_off = round(grand_total) - grand_total
        final_total = round(grand_total)
        
        self.lbl_subtotal.config(text=f"{subtotal:.2f}")
        self.lbl_cgst.config(text=f"{total_cgst:.2f}")
        self.lbl_sgst.config(text=f"{total_sgst:.2f}")
        self.lbl_igst.config(text=f"{total_igst:.2f}")
        self.lbl_round.config(text=f"{round_off:.2f}")
        self.lbl_grand_total.config(text=f"₹ {final_total:.2f}")

    def save_invoice(self, print_it=True):
        if not self.cart:
            messagebox.showerror("Error", "Cart is empty")
            return
            
        # Todo: Save to DB
        messagebox.showinfo("Success", "Invoice Saved!")
        self.destroy()
        self.parent.load_invoices()
