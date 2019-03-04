import time
import random

def blackbox_function_default(inMap):
    outMap = inMap
    return outMap

def blackbox_function_identity(inMap):
    outMap = inMap
    return outMap

def blackbox_function_math(inMap):
    f1=int(inMap['figure1'])
    f2=int(inMap['figure2'])
    mylabel=inMap['mylabel']

    if 'please_crash_me' in mylabel:
        raise Exception("User-initiated purposeful failure! Go Figure")

    outMap = {
        'sum':f1+f2, 
        'product':f1*f2,
        'max':max([f1,f2]),
        'suminwords': mylabel + " " + str(int(f1+f2))
        }
    return outMap    

def blackbox_function_advanced_math(inMap):
    f1=int(inMap['figure1'])
    f2=int(inMap['figure2'])
    mylabel=inMap['mylabel']

    if 'please_crash_me' in mylabel:
        raise Exception("User-initiated purposeful failure! Go Figure")

    outMap = {
        'division':f1/f2, 
        'modulo':f1%f2,
        'min':min([f1,f2]),
        'productinwords': mylabel + " " + str(int(f1*f2))
        }
    return outMap        

def blackbox_function_math_superslow(inMap):
    f1=int(inMap['figure1'])
    f2=int(inMap['figure2'])
    mylabel=inMap['mylabel']

    # artificial delay
    on_time_calcs_ratio = 0.99
    if 'on_time_calcs_ratio' in inMap:
        on_time_calcs_ratio=int(inMap['on_time_calcs_ratio'])

    if random.random() >= 0.9999: # EXTREME SLOWDOWN!
        time.sleep(60)
    elif random.random() >= 0.999: # The 9-9-9 Plan!
        time.sleep(15)
    elif random.random() >= on_time_calcs_ratio: # Normal slowdown!
        time.sleep(1)

    if 'please_crash_me' in mylabel:
        raise Exception("User-initiated purposeful failure! Go Figure")

    outMap = {
        'sum':f1+f2, 
        'product':f1*f2,
        'max':max([f1,f2]),
        'suminwords': mylabel + " " + str(int(f1+f2))
        }
    return outMap     