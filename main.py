"""
Indian SMB ERP - Entry Point
"""
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.app import ERPApplication
from database.db_init import get_database

def main():
    # Initialize database on startup
    db = get_database()
    
    # Launch Application
    app = ERPApplication()
    app.mainloop()

if __name__ == "__main__":
    main()
