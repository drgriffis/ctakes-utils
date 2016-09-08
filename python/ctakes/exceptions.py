'''
Custom exceptions for cTAKES processing components
'''

class AttributeNotFoundException(KeyError):
    def __init_(self, attr_name):
        message = "No attribute named '%s' found in element." % attr_name
        super(AttributeNotFoundException, self).__init__(message)

class ElementNotFoundException(KeyError):
    def __init__(self, el_name):
        message = "No element named '%s' found in document." % el_name
        super(ElementNotFoundException, self).__init__(message)
