# Errors
UNAUTHORIZED                = {"status_code": 401, "message": "Unauthorized."} # API KEY does not matched
BAD_REQUEST                 = {"status_code": 400, "message": "Bad Request." } # Invalid Email, Username or Full Name
REDIS_ERROR                 = {"status_code": 500, "message": "Request cannot processed."} # Redis database error
TOO_MANY_REQUESTS           = {"status_code": 429, "message": "Too many requests."} # Too many requests sent by the client
MAX_ATTEMPTS_REACHED        = {"status_code": 403, "message": "Forbidden."} # When maximum attempts limit reached
EMAIL_TEMPLATE_ERROR        = {"status_code": 512, "message": "Request cannot processed."} # When email template error 
OTP_VERIFY_FAILED           = {"isVerified" : False} # When otp verification fails
DB_ERROR                    = {"status_code": 500, "message": "Request cannot processed."} # PostgreSQL database error
ALREADY_EXISTS              = {"status_code": 409, "message": "Conflict."} # Username already exists in the DB
BLOCKED_ACC_ACCESS          = {"status_code": 511, "message": "Forbidden" } # Account access is denied 