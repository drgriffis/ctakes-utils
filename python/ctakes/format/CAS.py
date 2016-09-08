'''
Methods for handling cTAKES CAS output.
'''

import codecs
import re
from . import common
from ..annotations import Mention
from ..exceptions import *

from denis.common import util

def getMentions(outputf):
    '''Get the (ambiguous) entity mentions from the XMI file,
    as a list of Mention objects.
    '''
    fsarrays, cur_fsarray, in_fsarray = [], None, False
    pln, tag_tokens = None, 0
    concepts, array_bounds = {}, {}

    hook = codecs.open(outputf, 'r')
    for line in hook:
        line = line.strip()

        if util.matchesRegex(_fsarray_start, line):
            # grab its bounds from the array_bounds map (should be stored already)
            try:
                ID = getAttributeValue(line, '_id')
                (start, stop) = array_bounds[ID]
                cur_fsarray = _FSArray(ID, start, stop)
                cur_fsarray.start, cur_fsarray.stop = start, stop
                in_fsarray = True
            except KeyError as e:
                pass    # there are _FSArrays for other purposes than just CUI storage
        elif util.matchesRegex(_fsarray_end, line) and in_fsarray:
            if len(cur_fsarray.concept_IDs) > 0: fsarrays.append(cur_fsarray)
            in_fsarray = False
        elif util.matchesRegex(_concept, line):
            _addConcept(line, concepts)

        elif in_fsarray and util.matchesRegex(_fsarray_item, line):
            mtch = re.findall(r'[0-9]+', line)
            assert len(mtch) == 1
            cur_fsarray.concept_IDs.append(mtch[0])

        elif util.matchesRegex(_entity_mention, line):
            _addMentionBounds(line, array_bounds)

    hook.close()
    return _FSArraysToMentions(fsarrays, concepts)

def getTokens(outputf, mentions=None):
    return common.getTokens(outputf, mentions=mentions, _token_regexes=_token_regexes)
common.inheritDocstring(getTokens, common.getTokens)

def getAttributeValue(line, attr_name):
    return common.getAttributeValue(line, attr_name)
common.inheritDocstring(getAttributeValue, common.getAttributeValue)


### FSArray handling #######

class _FSArray:
    def __init__(self, ID=None, start=0, stop=0):
        self.ID = ID
        self.start = start
        self.stop = stop
        self.concept_IDs = []

def _FSArraysToMentions(fsarrays, concepts):
    '''Convert FSArray objects referencing UmlsConcept instance IDs
    to Mention objects referencing corresponding CUIs.
    '''
    mentions = []
    for fsarr in fsarrays:
        cui_set = []
        for conceptid in fsarr.concept_IDs:
            try:
                cui_set.append(concepts[conceptid])
            except KeyError:
                pass
        if len(cui_set) > 0:
            mentions.append(Mention(
                CUIs=cui_set,
                bounds=(fsarr.start, fsarr.stop)
            ))
    return mentions

def _addConcept(line, concepts):
    '''Add an ID->CUI mapping from a UmlsConcept instance line
    '''
    ID, cui = getAttributeValue(line, '_id'), getAttributeValue(line, 'cui')
    concepts[ID] = cui

def _addMentionBounds(line, array_bounds):
    '''Add the character bounds for a tagged entity mention
    '''
    ID = getAttributeValue(line, '_ref_ontologyConceptArr')
    start = int(getAttributeValue(line, 'begin'))
    stop = int(getAttributeValue(line, 'end'))
    array_bounds[ID] = (start, stop)


### Regexes ################

def _compileRegex(ptrn):
    ptrn = r'^\s*%s' % ptrn
    return re.compile(ptrn)

_fsarray_start  = _compileRegex(r'<uima.cas.FSArray')
_fsarray_item   = _compileRegex(r'<i>')
_fsarray_end    = _compileRegex(r'</uima.cas.FSArray>')
_entity_mention = _compileRegex(r'<org.apache.ctakes.typesystem.type.textsem.[A-Za-z]*Mention .* _ref_ontologyConceptArr="[0-9]+"')
_concept        = _compileRegex(r'<org.apache.ctakes.typesystem.type.refsem.UmlsConcept')
_text           = _compileRegex(r'<uima.cas.Sofa')

_token_regexes = [
    _compileRegex(r'<org.apache.ctakes.typesystem.type.syntax.SymbolToken'),
    _compileRegex(r'<org.apache.ctakes.typesystem.type.syntax.WordToken'),
    _compileRegex(r'<org.apache.ctakes.typesystem.type.syntax.PunctuationToken'),
    _compileRegex(r'<org.apache.ctakes.typesystem.type.syntax.NumToken'),
    _compileRegex(r'<org.apache.ctakes.typesystem.type.syntax.ContractionToken'),
]
