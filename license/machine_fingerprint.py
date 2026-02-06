"""
Indian SMB ERP - Machine Fingerprint Utility
Hardware-based unique machine identification
"""
import hashlib
import platform
import uuid
import subprocess
import os


def get_mac_address() -> str:
    """Get MAC address as string"""
    mac = uuid.getnode()
    return ':'.join(('%012X' % mac)[i:i+2] for i in range(0, 12, 2))


def get_cpu_id() -> str:
    """Get CPU identifier"""
    try:
        if platform.system() == 'Windows':
            result = subprocess.run(
                ['wmic', 'cpu', 'get', 'processorid'],
                capture_output=True, text=True, timeout=5
            )
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                return lines[1].strip()
    except:
        pass
    return platform.processor()


def get_disk_serial() -> str:
    """Get primary disk serial number"""
    try:
        if platform.system() == 'Windows':
            result = subprocess.run(
                ['wmic', 'diskdrive', 'get', 'serialnumber'],
                capture_output=True, text=True, timeout=5
            )
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                return lines[1].strip()
    except:
        pass
    return ""


def get_motherboard_serial() -> str:
    """Get motherboard serial number"""
    try:
        if platform.system() == 'Windows':
            result = subprocess.run(
                ['wmic', 'baseboard', 'get', 'serialnumber'],
                capture_output=True, text=True, timeout=5
            )
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                return lines[1].strip()
    except:
        pass
    return ""


def generate_fingerprint() -> str:
    """
    Generate a unique machine fingerprint using multiple hardware identifiers.
    Returns a 32-character hex string.
    """
    components = [
        platform.node(),
        platform.machine(),
        get_cpu_id(),
        get_mac_address(),
        get_disk_serial(),
        get_motherboard_serial(),
    ]
    
    # Filter empty components and join
    valid_components = [c for c in components if c.strip()]
    fingerprint_source = '|'.join(valid_components)
    
    # Generate SHA-256 hash and truncate
    return hashlib.sha256(fingerprint_source.encode()).hexdigest()[:32]


def verify_fingerprint(stored: str) -> bool:
    """Verify if current machine matches stored fingerprint"""
    current = generate_fingerprint()
    return current == stored


def get_machine_info() -> dict:
    """Get readable machine information"""
    return {
        'hostname': platform.node(),
        'os': f"{platform.system()} {platform.release()}",
        'architecture': platform.machine(),
        'processor': platform.processor(),
        'fingerprint': generate_fingerprint()
    }


if __name__ == '__main__':
    print("Machine Fingerprint:", generate_fingerprint())
    print("\nMachine Info:")
    for k, v in get_machine_info().items():
        print(f"  {k}: {v}")
