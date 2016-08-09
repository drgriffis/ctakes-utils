'''
Methods for handling cTAKES XMI output.
'''

import re
from . import common

def compileTextsemRegex(annot_type):
    ptrn = r'^\s*<textsem:%s' % annot_type
    return re.compile(ptrn)

def getAttributeValue(line, attr_name):
    return common.getAttributeValue(line, attr_name)
