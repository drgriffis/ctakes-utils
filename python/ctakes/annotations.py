'''
Module for cTAKES data models.
'''

class Mention:
    def __init__(self, CUIs=[], bounds=None):
        self.CUIs = CUIs
        self.begin = bounds[0] if bounds != None else None
        self.end = bounds[1] if bounds != None else None
        self.text = None
