def blackbox_function_sales(inMap):

    name = f"{inMap['first']} {inMap['last']}"

    change = 20 - inMap['cost']

    if inMap['last_is_brown'] == 1:
        sib = 'sibling'
    else:
        sib = 'not sibling'

    if inMap['age_norm'] >= 0.5:
        dem = 'older'
    else:
        dem = 'younger'

    outMap = {
        'full_name': name,
        'change_from_a_20': change,
        'family_info': sib,
        'demographic': dem
    }

    return outMap

def blackbox_function_sales_no_inline_feats(inMap):

    name = f"{inMap['first']} {inMap['last']}"

    change = 20 - inMap['cost']

    outMap = {
        'full_name': name,
        'change_from_a_20': change
    }

    return outMap

def blackbox_function_crisk_only_inline_feats(inMap):

    print(inMap)

    risk_factor = 0.83

    if "age_bucketed" in inMap:
        risk_factor = inMap["age_bucketed"]/6
    if "gender_is_M" in inMap:
        if inMap["gender_is_M"]==1:
            risk_factor = risk_factor * 1.2 # male risk multiplier
    if "weight_norm" in inMap:
        if inMap["weight_norm"]>0.9:
            risk_factor = risk_factor * 1.2 # obesity risk multiplier

    outMap = {
        'risk_factor': risk_factor
    }

    return outMap