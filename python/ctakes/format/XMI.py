'''
Methods for handling cTAKES XMI output.
'''

import re
import codecs
import numpy as np
from . import common
from ..annotations import Mention
from ..exceptions import *

from denis.common import util

def getMentions(fpath):
    '''Get the (ambiguous) entity mentions from the XMI file,
    as a list of Mention objects.
    '''
    concept_sets, bounds = [], []
    concept_cui_map = {}

    hook = codecs.open(fpath, 'r', 'utf-8')
    for line in hook:
        if util.matchesRegex(_umls_concept, line):
            concept_id = getAttributeValue(line, 'id')
            concept_cui = getAttributeValue(line, 'cui')
            concept_cui_map[concept_id] = concept_cui
        else:
            for regex in _mention_regexes:
                if util.matchesRegex(regex, line):
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

def getTokens(outputf, mentions=None):
    return common.getTokens(outputf, mentions=mentions, _token_regexes=_token_regexes)
common.inheritDocstring(getTokens, common.getTokens)

def getAttributeValue(line, attr_name):
    return common.getAttributeValue(line, attr_name)
common.inheritDocstring(getAttributeValue, common.getAttributeValue)


### Regexes ################

def _compileRegex(sem_type, annot_type):
    ptrn = r'^\s*<%s:%s' % (sem_type, annot_type)
    return re.compile(ptrn)

_umls_concept = _compileRegex('refsem', 'UmlsConcept')
_mention_regexes = [
    _compileRegex('textsem', 'SignSymptomMention'),
    _compileRegex('textsem', 'DiseaseDisorderMention'),
    _compileRegex('textsem', 'MedicationMention'),
    _compileRegex('textsem', 'ProcedureMention'),
    _compileRegex('textsem', 'AnatomicalSiteMention')
]
_token_regexes = [
    _compileRegex('syntax', 'SymbolToken'),
    _compileRegex('syntax', 'WordToken'),
    _compileRegex('syntax', 'PunctuationToken'),
    _compileRegex('syntax', 'NumToken'),
    _compileRegex('syntax', 'ContractionToken')
]
