def looks_like_email(email: str) -> bool:
    if not email or '@' not in email or '.' not in email:
        return False
    if len(email) < 6:
        return False
    return True
