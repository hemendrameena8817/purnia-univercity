def calculate_paper_result(ese_marks, ese_max, cia_marks, cia_max, paper_type="HONOURS"):
    """
    Determines if a paper is passed. 
    A subject is passed ONLY IF both ESE and CIA parts meet the passing criteria.
    Hons: 45% to pass
    Subsidiary: 35% to pass
    """
    pass_pct = 45 if paper_type.upper() == "HONOURS" else 33
    
    # Check ESE
    ese_pass = True
    if ese_max > 0:
        ese_pass = (ese_marks / ese_max) * 100 >= pass_pct
        
    # Check CIA (or Practical)
    cia_pass = True
    if cia_max > 0:
        cia_pass = (cia_marks / cia_max) * 100 >= pass_pct
        
    return ese_pass and cia_pass

def determine_overall_result(hons_marks_data, sub_marks_data):
    """
    Calculates the overall result based on aggregate percentage.
    Criteria: 
    - Pass with Hons.: Passes all subjects individually.
    - PASS: Total marks >= Sum of (45% Honours Pass + 35% Subsidiary Pass).
    - FAIL: Otherwise.
    """
    total_subjects = len(hons_marks_data) + len(sub_marks_data)
    if total_subjects == 0: return "PENDING"

    total_obtained = 0.0
    total_pass_needed = 0.0
    passed_all_individually = True
    
    # Process Honours
    for p in hons_marks_data:
        # p: (ese_marks, ese_max, cia_marks, cia_max)
        m_ese, mx_ese, m_cia, mx_cia = p
        total_obtained += (m_ese + m_cia)
        # pass marks is 45% of max
        total_pass_needed += (mx_ese * 0.45) + (mx_cia * 0.45)
        
        if not calculate_paper_result(m_ese, mx_ese, m_cia, mx_cia, "HONOURS"):
            passed_all_individually = False
            
    # Process Subsidiary and Composition
    for p in sub_marks_data:
        m_ese, mx_ese, m_cia, mx_cia = p
        total_obtained += (m_ese + m_cia)
        # pass marks is 33% of max
        total_pass_needed += (mx_ese * 0.33) + (mx_cia * 0.33)
        
        if not calculate_paper_result(m_ese, mx_ese, m_cia, mx_cia, "SUBSIDIARY"):
            passed_all_individually = False

    # Final Decision
    if passed_all_individually:
        return "Pass with Hons."
    elif total_obtained >= total_pass_needed:
        # User said "Promoted means also pass" and "Basis upon check percent"
        return "PASS"
    else:

        return "FAIL"

def get_hons_classification(total_hons_marks, total_hons_max):
    """
    Degree class based on aggregate Honours percentage.
    """
    if not total_hons_max or total_hons_max == 0: return "PENDING"
    pct = (total_hons_marks / total_hons_max) * 100
    
    if pct >= 75: return "1st Class With Distinction"
    if pct >= 60: return "1st Class"
    if pct >= 45: return "2nd Class"
    return "FAIL"
