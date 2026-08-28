# Database Queries

SELECT_USER_DETAILS_BY_USERNAME = """--sql
    SELECT full_name, email_address, user_id, is_verified, is_active, password, salt, two_fa_enabled, profile_picture
    FROM users 
    WHERE username = $1 
    LIMIT 1
"""

SELECT_USER_DETAILS_BY_ID = """--sql
    SELECT full_name, user_id, email_address, username, two_fa_enabled, profile_picture, salt
    FROM users 
    WHERE user_id = $1 
    LIMIT 1
"""

SELECT_ID_NAME_BY_EMAIL = """--sql
    SELECT user_id, full_name
    FROM users
    WHERE email_address = $1
    LIMIT 1
"""

SELECT_ID_VER_STATUS_BY_EMAIL = """--sql
    SELECT user_id, is_verified
    FROM users
    WHERE email_address = $1
    LIMIT 1
"""

SELECT_USERNAME_BY_USERNAME = """--sql
    SELECT username 
    FROM users 
    WHERE username = $1 
    LIMIT 1
"""

SELECT_EMAIL_BY_EMAIL = """--sql
    SELECT email_address 
    FROM users 
    WHERE email_address = $1 
    LIMIT 1
"""

SELECT_ACC_VERIFICATION_STATUS_BY_USERNAME = """--sql
    SELECT is_verified 
    FROM users 
    WHERE username = $1 
    LIMIT 1
"""

SELECT_ACC_VERIFICATION_STATUS_BY_EMAIL = """--sql
    SELECT is_verified 
    FROM users 
    WHERE email_address = $1 
    LIMIT 1
"""

SELECT_PASSWORD_BY_ID = """--sql
    SELECT password 
    FROM users 
    WHERE user_id = $1 
    LIMIT 1
"""

UPDATE_PASSWORD_BY_ID = """--sql
    UPDATE users
    SET password = $1
    WHERE user_id = $2
"""

UPDATE_ACC_VERIFICATION_STATUS_BY_EMAIL = """--sql
    UPDATE users 
    SET is_verified = TRUE 
    WHERE email_address = $1
"""

UPDATE_LAST_LOGIN_AT_BY_USERNAME = """--sql
    UPDATE users
    SET last_login_at = $1
    WHERE username = $2
"""

UPDATE_LAST_USED_AT_BY_ID = """--sql
    UPDATE devices AS d
    SET last_used_at = $1
    FROM users AS u
    WHERE u.user_id = $2 AND u.user_id = d.user_id --  internally using join 
"""

UPDATE_TWO_FA_STATUS_BY_ID = """--sql
    UPDATE users
    SET two_fa_enabled = $1
    WHERE user_id = $2
"""

UPDATE_USERNAME_BY_ID = """--sql
    UPDATE users
    SET username = $1
    WHERE user_id = $2
"""

UPDATE_RETURN_PROFILE_PICTURE_PATH_BY_ID = """--sql
    WITH old AS (
        SELECT profile_picture
        FROM users
        WHERE user_id = $1
    )

    UPDATE users
    SET profile_picture = $2
    WHERE user_id = $1
    RETURNING (
        SELECT profile_picture FROM old
    ) AS old_profile_picture;
"""

DELETE_PROFILE_PICTURE_PATH_AND_RETURN_BACK_BY_ID = """--sql
    WITH old AS (
        SELECT profile_picture
        FROM users
        WHERE user_id = $1
    )
    UPDATE users
    SET profile_picture = NULL
    WHERE user_id = $1
    RETURNING (SELECT profile_picture FROM old) AS deleted_profile_picture;
"""

INSERT_CREDENTIALS = """--sql
    WITH new_user AS (
        INSERT INTO users (
            full_name, username, email_address, password, created_at, last_login_at, is_active, salt
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING user_id
    )
    INSERT INTO devices (
        user_id, device_name, device_identifier, os_type, os_version, kernel_version, last_ip, app_version
    )
    SELECT user_id, $9, $10, $11, $12, $13, $14, $15 
    FROM new_user
"""

DELETE_ACCOUNT_RETURN_PROFILE_PICTURE_PATH_BY_ID = """--sql
    DELETE FROM users
    WHERE user_id = $1
    RETURNING profile_picture AS deleted_profile_picture;
"""