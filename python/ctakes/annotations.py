'''
Module for cTAKES data models.
'''

class Mention:
    def __init__(self, CUIs=[], bounds=None):
        self.CUIs = CUIs
        self.begin = bounds[0] if bounds != None else None
        self.end = bounds[1] if bounds != None else None
        self.text = None

    def __repr__(self):
        return '{ CUIs: [%s] Begin: %d End: %d Text: "%s" }' % (
            ','.join(self.CUIs),
            self.begin,
            self.end,
            self.text
        )

    def __eq__(self, other):
        for c in self.CUIs:
            if not c in other.CUIs: return False
        return self.begin == other.begin \
           and self.end == other.end \
           and self.text == other.text

    def __neq__(self, other):
        return not self.__eq__(other)
