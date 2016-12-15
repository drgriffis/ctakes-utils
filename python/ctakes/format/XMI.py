'''
Methods for handling cTAKES XMI output.

@depends BeautifulSoup
'''

import re
import codecs
from bs4 import BeautifulSoup
from . import common
from ..annotations import Mention
from ..exceptions import *

def getMentions(fpath):
    '''Get the (ambiguous) entity mentions from the XMI file,
    as a list of Mention objects.
    '''
    concept_sets, bounds = [], []
    concept_cui_map = {}

    hook = codecs.open(fpath, 'r', 'utf-8')
    for line in hook:
        if common.matchesRegex(_umls_concept, line):
            concept_id = getAttributeValue(line, 'id')
            concept_cui = getAttributeValue(line, 'cui')
            concept_cui_map[concept_id] = concept_cui
        else:
            for regex in _mention_regexes:
                if common.matchesRegex(regex, line):
                    try:
                        concept_ids = getAttributeValue(line, 'ontologyConceptArr').split(' ')
                    except AttributeNotFoundException:
                        continue
                    concept_sets.append(concept_ids)
                    bounds.append((
                        int(getAttributeValue(line, 'begin')),
                        int(getAttributeValue(line, 'end'))
                    ))
                    break   # only one mention type for any given line
    hook.close()

    # replace concept IDs in mentions with CUIs
    cui_sets = []
    for concept_set in concept_sets:
        cui_sets.append([
            concept_cui_map[concept_id] for concept_id in concept_set
        ])

    # build data models
    assert len(bounds) == len(cui_sets)
    mentions = []
    for i in range(len(cui_sets)):
        mentions.append(Mention(
            CUIs=cui_sets[i],
            bounds=bounds[i]
        ))
    return mentions

def getDocumentID(fpath):
    '''Returns the name of the original file cTAKES parsed
    to generate this output.
    '''
    hook = codecs.open(fpath, 'r', 'utf-8')
    contents = hook.read()
    hook.close()

    soup = BeautifulSoup(contents, 'lxml-xml')
    return soup.XMI.DocumentID['documentID']

def getTokens(outputf, mentions=None, get_POS_tags=False, words_only=False):
    if words_only: token_types = _text_token_types
    else: token_types = _token_types
    return common.getTokens(outputf, mentions=mentions, get_POS_tags=get_POS_tags,
        _token_types=token_types)
common.inheritDocstring(getTokens, common.getTokens)

def getAttributeValue(line, attr_name):
    return common.getAttributeValue(line, attr_name)
common.inheritDocstring(getAttributeValue, common.getAttributeValue)


### Regexes ################

def _compileRegex(sem_type, annot_type):
    ptrn = r'^\s*<%s:%s' % (sem_type, annot_type)
    return re.compile(ptrn)
    
def _prepareSearches(*ns_node_types):
    prepared = []
    for (ns, nodename) in ns_node_types:
        prepared.append( (nodename, _compileRegex(ns, nodename)) )
    return prepared

_umls_concept = _compileRegex('refsem', 'UmlsConcept')
_mention_regexes = [
    _compileRegex('textsem', 'SignSymptomMention'),
    _compileRegex('textsem', 'DiseaseDisorderMention'),
    _compileRegex('textsem', 'MedicationMention'),
    _compileRegex('textsem', 'ProcedureMention'),
    _compileRegex('textsem', 'AnatomicalSiteMention')
]
_text_token_type_set = [
    ('syntax', 'WordToken'),
    ('syntax', 'NumToken'),
    ('syntax', 'ContractionToken')
]
_text_token_types = _prepareSearches(*_text_token_type_set)
_token_types = _prepareSearches(
    ('syntax', 'SymbolToken'),
    ('syntax', 'PunctuationToken'),
    *_text_token_type_set
)