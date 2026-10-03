import os
import time
import random

def dprint(text="", delay="1"):
    print(text)
    time.sleep(delay)
    os.system("cls")
    
def wprint(text="", delay="1"):
    print(text)
    time.sleep(delay)
    
def ra(low=False):
    apbLow = "qwertyuiopasdfghjklzxcvbnmQWRTIOPSDFGHJKLZXCVBNM1234567890"
    apb = "QWERTYUIOPASDFGHJKLZXCVBNM1234567890"
    if low == True:
        return str(random.choice(apbLow))
    elif low == False:
        return str(random.choice(apb))
    else:
        print("what?")
        
def cls():
    os.system("cls")