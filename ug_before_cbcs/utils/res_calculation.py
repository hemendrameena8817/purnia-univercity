
def calculate_ba_hons_part1_result(hons_total_obt, hons_total_max, sub1_total_obt, sub1_total_max, sub2_total_obt, sub2_total_max, comp_total_obt, comp_total_max):
    """
    Calculates the result status for BA Honours Part 1.
    
    Rules:
    - Pass Marks in Hons. Sub : 45%
    - Pass Marks in Subsidiary Sub : 33%
    - Pass Marks in Composition Sub : 33%
    
    Result Status:
    - PASS WITH HONS: A student passes in all subjects
    - PROMOTED: A student fails in maximum two subjects
    - FAIL: A student fails in three or more subjects
    """
    failed_count = 0
    
    # Honours Pass Check (45%)
    if hons_total_obt < (hons_total_max * 0.45):
        failed_count += 1
        
    # Subsidiary 1 Pass Check (33%)
    if sub1_total_max > 0 and sub1_total_obt < (sub1_total_max * 0.33):
        failed_count += 1
        
    # Subsidiary 2 Pass Check (33%)
    if sub2_total_max > 0 and sub2_total_obt < (sub2_total_max * 0.33):
        failed_count += 1
        
    # Composition Pass Check (33%)
    if comp_total_max > 0 and comp_total_obt < (comp_total_max * 0.33):
        failed_count += 1
        
    if failed_count == 0:
        return "PASS WITH HONS"
    elif failed_count <= 2:
        return "PROMOTED"
    else:
        return "FAIL"
