'''
Shared methods for cTAKES output file format processing.

Not included in from ctakes.format import *
'''

import re
import codecs
import numpy as np
from bs4 import BeautifulSoup
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

def getTokens(fpath, mentions=None, _token_types=[]):
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
        fpath        :: path to XMI file to process
        mentions     :: (optional) list of Mention objects to include
                        in place of the appropriate token 
    '''

    # if including mentions, index them by beginning index
    # (may be multiple beginning at same index)
    if mentions != None:
        indexed_mentions = {}
        for m in mentions:
            if indexed_mentions.get(m.begin, None) == None: indexed_mentions[m.begin] = []
            indexed_mentions[m.begin].append(m)

    # storage for instances of each token type
    tokens = [[] for _ in _token_types]
    # storage for starting bound of token type instances
    starts = [[] for _ in _token_types]
    
    # parse the XML file
    hook = codecs.open(fpath, 'r', 'utf-8')
    soup = BeautifulSoup(hook.read(), 'lxml-xml')
    hook.close()
    
    # iterate over the types of token nodes we're looking for
    for (node_type, regex) in _token_types:
        # get the child nodes and validate their namespace
        candidate_nodes, validated_nodes = soup.findChildren(node_type), []
        for node in candidate_nodes:
            if matchesRegex(regex, repr(node)): validated_nodes.append(node)
        # sort them by beginning index
        node_sorter = { int(node['begin']): node for node in validated_nodes }
        assert len(node_sorter) == len(validated_nodes)  # no duplicate 'begin' indices
        indices, sorted_nodes = list(node_sorter.keys()), []
        indices.sort()
        for index in indices:
            sorted_nodes.append(node_sorter[index])
        # pull out token and beginning index, store separately
        typed_tokens, typed_starts = [], []
        for node in sorted_nodes:
            typed_tokens.append(node['normalizedForm'])
            typed_starts.append(int(node['begin']))
        tokens.append(typed_tokens)
        starts.append(typed_starts)
    
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
