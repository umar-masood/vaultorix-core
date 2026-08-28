INSERT_BUG_REPORT_DETAILS = """--sql
    INSERT INTO bug_reports (
        user_id, 
        device_id, 
        subject,
        description, 
        screenshot_url, 
        created_at, 
        app_version,
        current_status 
    )
    VALUES (
        $1, 
        (SELECT device_id FROM devices WHERE user_id = $1 LIMIT 1), 
        $2, $3, $4, $5, $6, $7
    )
"""