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

def getTokens(fpath, mentions=None):
    '''Get the ordered list of tokens from the document, as
    tokenized by cTAKES.

    Parameters:
        fpath    :: path to XMI file to process
        mentions :: (optional) list of Mention objects to include
                    in place of the appropriate token
    '''
    ### Assumes tokens of each type are stored in the file in sorted order.

    # if including mentions, index them by beginning index
    if mentions != None: indexed_mentions = { m.begin:m for m in mentions }

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
    starts_remaining = []
    for i in range(len(starts)):
        if len(starts[i]) > 0: starts_remaining.append((i,starts[i]))
    cur_mention = None
    while len(starts_remaining) > 0:
        # find the next token type from the text
        next_starts = [start[0] for (_,start) in starts_remaining]
        next_starts_ix = np.argmin(next_starts)
        next_tokentype = starts_remaining[next_starts_ix][0]
        # get the next token
        next_token = tokens[next_tokentype].pop(0)
        next_token_start = starts_remaining[next_starts_ix][1][0]

        # if still in a mention
        if cur_mention != None and cur_mention.end > next_token_start:
            cur_mention.text.append(next_token)
        # if just completed a mention
        elif cur_mention != None and cur_mention.end <= next_token_start:
            # flush the completed mention
            cur_mention.text = ' '.join(cur_mention.text)
            ordered_tokens.append(cur_mention)
            cur_mention = None
            # add the token
            ordered_tokens.append(next_token)
        # if starting a mention
        elif mentions != None and indexed_mentions.get(next_token_start, None) != None:
            cur_mention = indexed_mentions[next_token_start]
            cur_mention.text = [next_token]
        # otherwise, just add the word
        else:
            ordered_tokens.append(next_token)

        # remove the starting index
        starts_remaining[next_starts_ix][1].pop(0)
        # check if any token types are complete
        new_starts_remaining = []
        for (i,start) in starts_remaining:
            if len(start) > 0: new_starts_remaining.append((i,start))
        starts_remaining = new_starts_remaining

    # check if still have a mention buffered
    if cur_mention != None:
        cur_mention.text = ' '.join(cur_mention.text)
        ordered_tokens.append(cur_mention)

    return ordered_tokens

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

def getAttributeValue(line, attr_name):
    return common.getAttributeValue(line, attr_name)


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
