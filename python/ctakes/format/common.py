'''
Shared methods for cTAKES output file format processing.

Not included in from ctakes.format import *
'''

import re

def getAttributeValue(line, attr_name):
    match = re.findall('%s=".+"' % attr_name, line)
    assert len(match) == 1
    match = match[0]

    opn = match.index('"')
    cls = match[opn+1:].index('"')
    return match[opn+1:opn+cls+1]
