def normalize_semester(semester):
    """Convert semester names to consistent format (1ST, 2ND, etc.)"""
    semester_mapping = {
        '1st': '1ST', 'first': '1ST', '1': '1ST',
        'part i': '1ST', 'part-i': '1ST', 'parti': '1ST', 'part 1': '1ST',
        '2nd': '2ND', 'second': '2ND', '2': '2ND', 
        'part ii': '2ND', 'part-ii': '2ND', 'partii': '2ND', 'part 2': '2ND',
        '3rd': '3RD', 'third': '3RD', '3': '3RD',
        'part iii': '3RD', 'part-iii': '3RD', 'partiii': '3RD', 'part 3': '3RD',
        '4th': '4TH', 'fourth': '4TH', '4': '4TH',
        '5th': '5TH', 'fifth': '5TH', '5': '5TH',
        '6th': '6TH', 'sixth': '6TH', '6': '6TH'
    }
    return semester_mapping.get(semester.lower(), semester.upper())
