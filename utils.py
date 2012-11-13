'''
Created on Nov 12, 2012

@author: ivan
'''

def list_to_string(lst):
    return ', '.join(map(lambda x: str(x),lst))

def string_to_list(str):
    return map(lambda x: int(x.strip()), str.split(','))