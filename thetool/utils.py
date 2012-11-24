'''
Created on Nov 12, 2012

@author: ivan
'''
from collections import deque
from array import array
def list_to_string(lst):
    return ', '.join(map(lambda x: str(x),lst))

def string_to_list(str):
    l=filter(lambda i:i.strip(), str.split(','))
    return map(lambda x: int(x.strip()), l)

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

def ip4_to_number(adr, rev=False):
    
    bytes_adr=map(lambda x: int(x.strip()),adr.split('.'))
    if not len(bytes_adr)==4:
        raise ValueError("Must be exactly 4 numbers")
    if not rev:
        bytes_adr=reversed(bytes_adr)
    num=0
    for b in bytes_adr:
        if b>255:
            raise ValueError('address numbers must be bytes')
        num=num << 8
        num |= b
    return num

def match_ip(ip1,ip2, mask):
    mask=ip4_to_number(mask)
    ip1=ip4_to_number(ip1) & mask
    ip2=ip4_to_number(ip2) & mask
    return ip1==ip2
    
       
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
    