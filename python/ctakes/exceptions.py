'''
Custom exceptions for cTAKES processing components
'''

class AttributeNotFoundException(KeyError):
    def __init_(self, attr_name):
        message = "No attribute named '%s' found in element."
        super(AttributeNotFoundException, self).__init__(message)
