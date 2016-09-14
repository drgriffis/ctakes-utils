'''
Shared methods for cTAKES output file format processing.

Not included in from ctakes.format import *
'''

import re
import codecs
import numpy as np
from ..exceptions import *

def getAttributeValue(line, attr_name):
    '''Return the value of the specified attribute in the input line
    '''
    match = re.findall('%s=".+"' % attr_name, line)
    if len(match) != 1:
        raise AttributeNotFoundException(attr_name)
    match = match[0]

    opn = match.index('"')
    cls = match[opn+1:].index('"')
    return match[opn+1:opn+cls+1]

def getTokens(fpath, mentions=None, _token_regexes=[]):
    '''Get the ordered list of tokens from the document, as
    tokenized by cTAKES.

    If list of Mentions is provided, the token list will consist
    of the following types:
     - str : non-mention token
     - Mention : non-overlapping entity mention
     - list : overlapping entity mentions within the same text span;
              each item consists of non-mention tokens and a single Mention
              e.g. [(Mention:"weight loss"), ("weight", Mention:"loss")]

    Parameters:
        fpath    :: path to XMI file to process
        mentions :: (optional) list of Mention objects to include
                    in place of the appropriate token
    '''
    ### Assumes tokens of each type are stored in the file in sorted order.

    # if including mentions, index them by beginning index
    # (may be multiple beginning at same index)
    if mentions != None:
        indexed_mentions = {}
        for m in mentions:
            if indexed_mentions.get(m.begin, None) == None: indexed_mentions[m.begin] = []
            indexed_mentions[m.begin].append(m)

    # storage for instances of each token type
    tokens = [[] for _ in _token_regexes]
    # storage for starting bound of token type instances
    starts = [[] for _ in _token_regexes]

    # read the tokens from the XMI file
    hook = codecs.open(fpath, 'r', 'utf-8')
    for line in hook:
        for i in range(len(_token_regexes)):
            if matchesRegex(_token_regexes[i], line):
                tokens[i].append(getAttributeValue(line, 'normalizedForm'))
                starts[i].append(int(getAttributeValue(line, 'begin')))
    hook.close()

    ordered_tokens = []

    # starts_remaining tracks the start indices for the token types left
    # to empty; contains pairs of token type (index) and start indices
    starts_remaining = []
    for i in range(len(starts)):
        if len(starts[i]) > 0: starts_remaining.append((i,starts[i]))
    
    cur_mentions = []   # current list of overlapping mentions
    overlap_sofar = []  # tokens in the current overlap preceding the next mention
    in_mention = False  # are we currently in >0 mentions?

    while len(starts_remaining) > 0:
        # find the next token type from the text
        next_starts = [start[0] for (_,start) in starts_remaining]
        next_starts_ix = np.argmin(next_starts)
        next_tokentype = starts_remaining[next_starts_ix][0]
        # get the next token
        next_token = tokens[next_tokentype].pop(0)
        next_token_start = starts_remaining[next_starts_ix][1][0]

        # if still in one or more mentions
        if in_mention:
            # check for completed mentions and add token appropriately
            in_mention = False
            for (before, m, after) in cur_mentions:
                if m.end > next_token_start:
                    m.text.append(next_token)
                    in_mention = True
                else:
                    after.append(next_token)

            # if all mentions completed, flush them as a block
            if not in_mention:
                for (before, m, after) in cur_mentions:
                    m.text = ' '.join(m.text)
                    after.pop(-1) # the last token is spurious
                ordered_tokens.append(cur_mentions)
                # and reset the overlap trackers
                cur_mentions, overlap_sofar = [], []

        # if starting a mention
        if mentions != None and indexed_mentions.get(next_token_start, None) != None:
            new_mentions = []
            for m in indexed_mentions[next_token_start]:
                m.text = [next_token]
                cur_mentions.append([ overlap_sofar.copy(), m, [] ])
            overlap_sofar.append(next_token)
            in_mention = True

        # otherwise, just add the word
        if not in_mention:
            ordered_tokens.append(next_token)

        # remove the starting index
        starts_remaining[next_starts_ix][1].pop(0)
        # check if any token types are complete
        new_starts_remaining = []
        for (i,start) in starts_remaining:
            if len(start) > 0: new_starts_remaining.append((i,start))
        starts_remaining = new_starts_remaining

    # check if still have a mention buffered
    if in_mention:
        for (before, m, after) in cur_mentions:
            m.text = ' '.join(m.text)
        ordered_tokens.append(cur_mentions)

    # flatten mentions and contexts
    output_tokens = []
    for t in ordered_tokens:
        if type(t) == list:
            if len(t) == 1:
                (before, m, after) = t[0]
                output_tokens.append(m)
            else:
                output_tokens.append([
                    flatten([before, m, after])
                    for (before, m, after) in t
                ])
        else: output_tokens.append(t)

    return output_tokens


### Utility methods #####################

def matchesRegex(regex, string):
    '''Returns Boolean indicating if the input regex found a positive (non-zero)
    match in the input string.
    '''
    mtch = re.match(regex, string)
    return mtch != None and mtch.span() != (0,0)

def flatten(arr):
    '''Given an array of N-dimensional objects (N can vary), returns 1-dimensional
    list of the contained objects.
    '''
    results = []
    for el in arr:
        if type(el) == list or type(el) == tuple: results.extend(flatten(el))
        else: results.append(el)
    return results


### Inheritance methods #################

def inheritDocstring(local, src):
    local.__doc__ = src.__doc__
