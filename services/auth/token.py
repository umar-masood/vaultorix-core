import jwt, uuid, secrets, os
from datetime import datetime, timedelta, timezone
from db.redis import redis_conn, connect_to_redis
from utils.logger import log
from fastapi import Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Generate Token
def generate_token(user_id : int, token_type : str = "Refresh") -> str:
    """
    This function generates a new access or refresh token and return as string.
    """
    # Payload    
    now = datetime.now(timezone.utc)

    if (token_type == "Access"):
        exp = now + timedelta(seconds = int(os.getenv("ACCESS_TOKEN_EXPIRY")))
    else:
        exp = now + timedelta(seconds = int(os.getenv("REFRESH_TOKEN_EXPIRY")))

    payload = {
        "sub"    : str(user_id), # to satisfy the jwt requirement of must having str insted of int
        "type"   : token_type.lower(),
        "iat"    : now,
        "nbf"    : now,
        "exp"    : exp,
        "jti"    : str(uuid.uuid4()),
        "nonce"  : secrets.token_urlsafe(32)
    }

    # Algorithm
    ALGORITHM = 'HS256'

    # Token
    token = jwt.encode(payload = payload, 
                       key = os.getenv("TOKEN_SECRET", "NULL"), 
                       algorithm = ALGORITHM
                       )

    return token

# Extract Token
security = HTTPBearer(auto_error = False)
async def get_token(auth_details : HTTPAuthorizationCredentials = Security(security)) -> str | None:
    """
    This function extracts access or refresh token from header and return it as a string otherwise return None
    """
    if not auth_details:
        return None
    
    if not auth_details.credentials:
        return None
    
    return auth_details.credentials

# Verify Token
def verify_token(token : str):
    """
    This functon verify the following things of token:
    - Header
    - Payload
    - Signature
    
    Return payload if it is valid otherwise return None
    """
    if not token:
        return None

    try:
        payload = jwt.decode(token, 
                             os.getenv("TOKEN_SECRET", "NULL"), 
                             algorithms = ['HS256']
                            )
        return payload

    except Exception as ex:
        log.error(f"Verification of Token failed: {ex}")

# Storing Token
async def store_token(user_id : int, payload : dict, token_type : str = "Refresh") -> None:
    """
    This function stores access or refresh token in Redis database
    """
    key = f'{user_id}:{token_type}Token'

    await redis_conn.set(key, 
                         str(payload['jti']), 
                         ex = int(os.getenv("ACCESS_TOKEN_EXPIRY", "NULL")) if token_type == "Access" 
                         else int(os.getenv("REFRESH_TOKEN_EXPIRY", "NULL"))
                        )

# Checking existence of Token in redis
async def check_token_in_db(user_id : int, token_type : str = "Refresh") -> bool:
    """
    This function checks whether the provided token exists in Redis database.
    Returns True if exists, otherwise False
    """
    key = f'{user_id}:{token_type}Token'
    response = await redis_conn.get(key)
    
    if response is not None:
        return True
    else:
        return False

# Verifying token with stored token in redis
async def verify_token_with_db(user_id : int, token_type : str, payload : dict) -> bool:
    """
    This function verifies the access or refresh token with respective tokin inside redis.
    Returns True if it exists, otherwise False
    """
    key = f'{user_id}:{token_type}Token'
    token = await redis_conn.get(key)

    if token is not None:
        if token == payload['jti']:
            return True
    
    return False

# Revoking Token from redis
async def revoke_token(user_id: str, token_type : str = "Refresh"):
    """
    This function removes access or refresh token entirely from redis database.
    """
    key = f'{user_id}:{token_type}Token'
    await redis_conn.delete(key)

## Validating token
async def validate_token(token: str, token_type : str = "Refresh") -> dict | None:
    """
    This function will validate the provided refresh token which includes:
        - Checking its length
        - Checking its existence in Redis (does it exist?) - only for refresh token
        - Extracting payload from token in case if it is valid
        - Matching token with the token stored in Redis - only for refresh token

    When all above things are validated, it will return payload otherwise None 

    `Note:` The refresh token is long lived while the access token is for short interval that's why we will ignore checking its existence inside Redis (Access Token).
    """
    # Checking empty or invalid length token (small optimization - reduced calls to DB)
    if not token or len(token) < 40:
        return None
   
    # Verifying Token (Extracting payload if it is valid)
    token_payload = verify_token(token)
    if token_payload is None:
        return None 
    
    # Extracting user id from token payload
    user_id = token_payload["sub"]
    if not user_id:
        return None

    # Check in db if it is Refresh
    if token_type == "Refresh": 

        # Redis Database Connection Check
        if not await connect_to_redis():
            log.error(f"Failed to connect to the redis.")
            return None
        
        # Checking token in redis
        if not await check_token_in_db(user_id, token_type):
            log.warning(f"{token_type} token does not exists in Redis provided by {user_id}")
            return None

        # Verifying token with stored token in redis
        if not await verify_token_with_db(user_id, token_type, token_payload):
            log.warning(f"The {token_type} token does not matched with the token stored in redis provided by {user_id}")
            return None

    return token_payload
    