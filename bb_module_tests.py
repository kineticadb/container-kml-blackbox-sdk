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

