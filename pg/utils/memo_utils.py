def get_ordinal(n):
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd',4:'th'}.get(n % 10, 'th')
    return f"{n}{suffix}"
