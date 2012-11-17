'''
Created on Nov 12, 2012

@author: ivan
'''
from collections import deque
from array import array
def list_to_string(lst):
    return ', '.join(map(lambda x: str(x),lst))

def string_to_list(str):
    return map(lambda x: int(x.strip()), str.split(','))

def ip4_to_str(num, rev=False):
    address=deque()
    for i in range(4):
        b=num & 0xFF
        if rev:
            address.appendleft(b )
        else:
            address.append(b)
        num=num >> 8
    return '.'.join(map(lambda b: str(b), address))
        
def bytes_to_string(blist):
    if not blist:
        return None
    return array('B',blist).tostring()

def bytes_to_mac(blist):
    return ':'.join(map(lambda b: hex(b)[2:], blist))

def byte_to_mask(b):
    mask=0xFFFFFFFF
    net_mask=(mask<<(32-b))&mask
    return ip4_to_str(net_mask, True)
    