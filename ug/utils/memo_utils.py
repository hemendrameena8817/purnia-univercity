def get_ordinal(num):
    """
    Returns the ordinal representation of a number (1st, 2nd, 3rd, etc.)
    """
    if not num:
        return ""
    
    try:
        n = int(num)
    except (ValueError, TypeError):
        return str(num)

    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    else:
        suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
    
    return f"{n}{suffix}"
