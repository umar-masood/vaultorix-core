import re, os
from fastapi import Request
from nacl import pwhash

# Device ID Validation
def is_valid_device_id(device_id : str) -> bool:
    rexp = re.compile(r'^[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12}$')
    if rexp.match(device_id):
        return True
    return False

# Client IP Handling
async def get_client_real_ip(request: Request) -> str:
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "0.0.0.0"

# API Key Verification
def verify_api_key(request : Request) -> bool:
    api_key = request.headers.get("api_key")

    if not api_key or api_key != os.getenv("SERVER_API_KEY"):
        return False
    
    return True

# Hashing Password
def hash_password(password : str) -> str:
    return pwhash.str(password.encode('utf-8'), 
                      pwhash.OPSLIMIT_MODERATE, 
                      pwhash.MEMLIMIT_MODERATE).decode('utf-8')

# Verify Password
def verify_password(curr_pwd : bytes, stored_pwd_hash : bytes) -> bool:
    """ 
    This function checks whether the current password hash match with the stored one.
    Returns True if matched otherwise False
    """
    try:
        pwhash.verify(stored_pwd_hash, curr_pwd)
        return True
    except Exception:
        return False
    
# Email Validation
def is_valid_email(email: str = '') -> bool:
    if not isinstance(email, str):
        return False

    if not email or '@' not in email or email.count('@') != 1:
        return False
    
    if ' ' in email or '\t' in email:
        return False

    local, domain = email.split('@')

    if not local or not domain:
        return False

    if local.startswith('.') or local.endswith('.') or '..' in local:
        return False

    if domain.startswith('.') or domain.endswith('.') or '..' in domain:
        return False

    if '.' not in domain:
        return False

    if any(ord(ch) > 127 for ch in email):
        return False

    local_re = re.compile(r'^[A-Za-z0-9._%+-]+$')
    domain_re = re.compile(r'^(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,24}$')

    if not local_re.match(local) or not domain_re.match(domain):
        return False

    if any(not label or label.startswith('-') or label.endswith('-') for label in domain.split('.')):
        return False

    return True

# Username Validation
def is_valid_username(username: str = '') -> bool:
    if not isinstance(username, str):
        return False

    if not username:
        return False

    if len(username) < 3 or len(username) > 20:
        return False

    pattern = re.compile(r'^[A-Za-z0-9._-]+$')
    if not pattern.match(username):
        return False

    if username[0] in '-._' or username[-1] in '-._':
        return False

    if ' ' in username:
        return False

    if '..' in username or '__' in username or '--' in username:
        return False

    if not username[0].isalpha():
        return False
    
    return True

# Full Name Validation
def is_valid_name(name : str = '') -> bool:
    if not isinstance(name, str):
        return False

    if not name: 
        return False
    
    if '  ' in name:
        return False
    
    if not re.match(r'^[A-Za-z ]+$', name):
        return False
    
    if len(name) < 3 or len(name) > 50:
        return False
    
    if not name[0].isupper():
        return False
    
    if not name[0].isalpha():
        return False

    return True

# Password Validation
def is_valid_password(password: str) -> bool:
    has_length  : bool = len(password) >= 8
    has_upper   : bool = False
    has_lower   : bool = False
    has_digit   : bool = False
    has_special : bool = False

    for ch in password:
        if 'A' <= ch <= 'Z':
            has_upper = True
        elif 'a' <= ch <= 'z':
            has_lower = True
        elif '0' <= ch <= '9':
            has_digit = True
        else:
            has_special = True

    return (
            has_length
        and has_upper
        and has_lower
        and has_digit
        and has_special
    )