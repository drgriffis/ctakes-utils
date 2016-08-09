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

def getTokens(fpath):
    '''Get the ordered list of tokens from the document, as
    tokenized by cTAKES.
    '''
    ### Assumes tokens of each type are stored in the file in sorted order.

    # storage for instances of each token type
    tokens = [[] for _ in _token_regexes]
    # storage for starting bound of token type instances
    starts = [[] for _ in _token_regexes]

    # read the tokens from the XMI file
    hook = codecs.open(fpath, 'r', 'utf-8')
    for line in hook:
        for i in range(len(_token_regexes)):
            if util.matchesRegex(_token_regexes[i], line):
                tokens[i].append(getAttributeValue(line, 'normalizedForm'))
                starts[i].append(int(getAttributeValue(line, 'begin')))
    hook.close()

    ordered_tokens = []

    # starts_remaining tracks the start indices for the token types left
    # to empty; contains pairs of token type (index) and start indices
    starts_remaining = [(i,starts[i]) for i in range(len(starts))]
    while len(starts_remaining) > 0:
        # find the next token type from the text
        next_starts = [start[0] for (_,start) in starts_remaining]
        next_tokentype = starts_remaining[np.argmin(next_starts)][0]
        # add the next token
        ordered_tokens.append(tokens[next_tokentype].pop(0))
        # and remove its starting index
        starts_remaining[np.argmin(next_starts)][1].pop(0)
        # check if any token types are complete
        new_starts_remaining = []
        for (i,start) in starts_remaining:
            if len(start) > 0: new_starts_remaining.append((i,start))
        starts_remaining = new_starts_remaining

    return ordered_tokens

def getConceptMentions(fpath):
    '''Get the (ambiguous) entity mentions from the XMI file,
    as a list of lists of CUIs.

    Each entry in the returned list represents a mention; the
    elements in that list are the different CUIs the mention
    was tagged with.
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

def compileRegex(sem_type, annot_type):
    ptrn = r'^\s*<%s:%s' % (sem_type, annot_type)
    return re.compile(ptrn)

def getAttributeValue(line, attr_name):
    return common.getAttributeValue(line, attr_name)


### Regexes ################

_umls_concept = compileRegex('refsem', 'UmlsConcept')
_mention_regexes = [
    compileRegex('textsem', 'SignSymptomMention'),
    compileRegex('textsem', 'DiseaseDisorderMention'),
    compileRegex('textsem', 'MedicationMention')
]
_token_regexes = [
    compileRegex('syntax', 'SymbolToken'),
    compileRegex('syntax', 'WordToken'),
    compileRegex('syntax', 'PunctuationToken'),
    compileRegex('syntax', 'NumToken'),
    compileRegex('syntax', 'ContractionToken')
]
