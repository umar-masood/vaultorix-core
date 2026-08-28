from redis.asyncio import Redis
from redis.exceptions import RedisError
from dotenv import load_dotenv
import os

load_dotenv()

redis_conn = Redis(
    host                = os.getenv("REDIS_HOST"),
    port                = os.getenv("REDIS_PORT"),
    password            = os.getenv("REDIS_PWD"),
    ssl                 = False,
    decode_responses    = True
)
    
# Test Redis connection
async def connect_to_redis() -> bool:
    """
    This method checks whether the connection to Redis has been established or not?

    Return True if done otherwise False
    """
    try:
        return await redis_conn.ping()
    except RedisError:
        return False
    
async def has_exceeded_limit(**kwargs) -> bool:
    """
    This function checks whether the max limit has been reached or not?
    
    - user_id
    - key_name
    - attempts_limit
    
    key = f'{user_id}:{key_name}'

    Returns True if yes otherwise False
    """
    key : str = None
    
    if "user_id" in kwargs:
        key = f"{kwargs['user_id']}:{kwargs['key_name']}"
    else:
        key = kwargs['key_name']

    attempts = await redis_conn.get(key)

    if attempts is None:
        attempts = 0
    
    return int(attempts) > kwargs['attempts_limit']
                                
async def increment_limit(**kwargs) -> None:
    """
    This function increments the attempts limit inside Redis by 1 and set its expiry
    
    - key_name (When this is used only - IP Limit Checker [Full Redis key must be passed as an argument to this function] )
    - user_id (When this is used then must provide both user_id and key_name to this function
        key = f'{user_id}:{key_name}'
    )
    - ex (Setting expiry of key)

    """
    key : str = None

    if "user_id" in kwargs:
        key = f"{kwargs['user_id']}:{kwargs['key_name']}"
    else:
        key = kwargs['key_name']
    
    attempts = await redis_conn.incr(key, 1)
    
    if attempts == 1 and "ex" in kwargs:
        await redis_conn.expire(key, kwargs['ex'])

async def reset_limit(**kwargs) -> None:
    """
    This function will reset the invalid attempts limit in database whenever user successfully done operation before reaching the end of attempts limit.

    It does not return anything, only updates status in database
    """
    key : str = None

    if "user_id" in kwargs:
        key = f"{kwargs['user_id']}:{kwargs['key_name']}"
    else:
        key = kwargs['key_name']
            
    await redis_conn.delete(key)