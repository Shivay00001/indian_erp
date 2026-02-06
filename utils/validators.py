"""
Indian SMB ERP - Validators
GST, PAN, email, phone, and invoice validation
"""
import re
from typing import Tuple


def validate_gstin(gstin: str) -> Tuple[bool, str]:
    """
    Validate Indian GSTIN (15 characters)
    Format: 22AAAAA0000A1Z5
    - First 2: State code (01-37)
    - Next 10: PAN
    - Next 1: Entity number (1-9, A-Z)
    - Next 1: Z (default)
    - Last 1: Checksum
    """
    if not gstin:
        return True, ""  # Optional field
    
    gstin = gstin.upper().strip()
    
    if len(gstin) != 15:
        return False, "GSTIN must be exactly 15 characters"
    
    pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
    if not re.match(pattern, gstin):
        return False, "Invalid GSTIN format"
    
    # Validate state code
    state_code = int(gstin[:2])
    valid_state_codes = [
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
        21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 97
    ]
    if state_code not in valid_state_codes:
        return False, "Invalid state code in GSTIN"
    
    return True, ""


def validate_pan(pan: str) -> Tuple[bool, str]:
    """
    Validate Indian PAN (10 characters)
    Format: AAAAA9999A
    - First 5: Alphabets
    - Next 4: Numbers
    - Last 1: Alphabet
    """
    if not pan:
        return True, ""  # Optional field
    
    pan = pan.upper().strip()
    
    if len(pan) != 10:
        return False, "PAN must be exactly 10 characters"
    
    pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
    if not re.match(pattern, pan):
        return False, "Invalid PAN format"
    
    return True, ""


def validate_email(email: str) -> Tuple[bool, str]:
    """Validate email address"""
    if not email:
        return True, ""
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Invalid email format"
    
    return True, ""


def validate_phone(phone: str) -> Tuple[bool, str]:
    """Validate Indian phone number"""
    if not phone:
        return True, ""
    
    # Remove common formatting
    phone = re.sub(r'[\s\-\(\)]', '', phone)
    
    # Remove country code if present
    if phone.startswith('+91'):
        phone = phone[3:]
    elif phone.startswith('91') and len(phone) > 10:
        phone = phone[2:]
    elif phone.startswith('0'):
        phone = phone[1:]
    
    if not phone.isdigit():
        return False, "Phone number should contain only digits"
    
    if len(phone) != 10:
        return False, "Phone number must be 10 digits"
    
    if phone[0] not in '6789':
        return False, "Invalid mobile number prefix"
    
    return True, phone


def validate_pincode(pincode: str) -> Tuple[bool, str]:
    """Validate Indian pincode"""
    if not pincode:
        return True, ""
    
    pincode = pincode.strip()
    if not pincode.isdigit() or len(pincode) != 6:
        return False, "Pincode must be 6 digits"
    
    if pincode[0] == '0':
        return False, "Invalid pincode"
    
    return True, ""


def validate_hsn_code(hsn: str) -> Tuple[bool, str]:
    """Validate HSN code (4, 6, or 8 digits)"""
    if not hsn:
        return True, ""
    
    hsn = hsn.strip()
    if not hsn.isdigit():
        return False, "HSN code must contain only digits"
    
    if len(hsn) not in [4, 6, 8]:
        return False, "HSN code must be 4, 6, or 8 digits"
    
    return True, ""


def validate_upi_id(upi_id: str) -> Tuple[bool, str]:
    """Validate UPI ID format"""
    if not upi_id:
        return True, ""
    
    pattern = r'^[a-zA-Z0-9.\-_]+@[a-zA-Z]+$'
    if not re.match(pattern, upi_id):
        return False, "Invalid UPI ID format (example: name@upi)"
    
    return True, ""


def validate_ifsc(ifsc: str) -> Tuple[bool, str]:
    """Validate IFSC code"""
    if not ifsc:
        return True, ""
    
    ifsc = ifsc.upper().strip()
    pattern = r'^[A-Z]{4}0[A-Z0-9]{6}$'
    if not re.match(pattern, ifsc):
        return False, "Invalid IFSC format (example: SBIN0001234)"
    
    return True, ""


def validate_bank_account(account: str) -> Tuple[bool, str]:
    """Validate bank account number"""
    if not account:
        return True, ""
    
    account = account.strip()
    if not account.isdigit():
        return False, "Account number must contain only digits"
    
    if len(account) < 9 or len(account) > 18:
        return False, "Account number should be 9-18 digits"
    
    return True, ""


def calculate_gst(amount: float, gst_rate: float, is_igst: bool = False) -> dict:
    """
    Calculate GST components
    Returns CGST, SGST (intra-state) or IGST (inter-state)
    """
    gst_amount = round(amount * gst_rate / 100, 2)
    
    if is_igst:
        return {
            'igst_rate': gst_rate,
            'igst_amount': gst_amount,
            'cgst_rate': 0,
            'cgst_amount': 0,
            'sgst_rate': 0,
            'sgst_amount': 0,
            'total_gst': gst_amount
        }
    else:
        half_rate = gst_rate / 2
        half_amount = round(gst_amount / 2, 2)
        return {
            'cgst_rate': half_rate,
            'cgst_amount': half_amount,
            'sgst_rate': half_rate,
            'sgst_amount': half_amount,
            'igst_rate': 0,
            'igst_amount': 0,
            'total_gst': half_amount * 2
        }


# Indian states with codes
INDIAN_STATES = {
    '01': 'Jammu & Kashmir',
    '02': 'Himachal Pradesh',
    '03': 'Punjab',
    '04': 'Chandigarh',
    '05': 'Uttarakhand',
    '06': 'Haryana',
    '07': 'Delhi',
    '08': 'Rajasthan',
    '09': 'Uttar Pradesh',
    '10': 'Bihar',
    '11': 'Sikkim',
    '12': 'Arunachal Pradesh',
    '13': 'Nagaland',
    '14': 'Manipur',
    '15': 'Mizoram',
    '16': 'Tripura',
    '17': 'Meghalaya',
    '18': 'Assam',
    '19': 'West Bengal',
    '20': 'Jharkhand',
    '21': 'Odisha',
    '22': 'Chhattisgarh',
    '23': 'Madhya Pradesh',
    '24': 'Gujarat',
    '25': 'Daman & Diu',
    '26': 'Dadra & Nagar Haveli',
    '27': 'Maharashtra',
    '28': 'Andhra Pradesh',
    '29': 'Karnataka',
    '30': 'Goa',
    '31': 'Lakshadweep',
    '32': 'Kerala',
    '33': 'Tamil Nadu',
    '34': 'Puducherry',
    '35': 'Andaman & Nicobar',
    '36': 'Telangana',
    '37': 'Andhra Pradesh (New)',
    '97': 'Other Territory',
}


def get_state_code(state: str) -> str:
    """Get state code from state name"""
    for code, name in INDIAN_STATES.items():
        if name.lower() == state.lower():
            return code
    return ''


def is_interstate(source_state: str, dest_state: str) -> bool:
    """Check if transaction is inter-state"""
    if not source_state or not dest_state:
        return False
    return source_state.lower().strip() != dest_state.lower().strip()
