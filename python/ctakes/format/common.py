'''
Shared methods for cTAKES output file format processing.

Not included in from ctakes.format import *
'''

import re
import codecs
import numpy as np
from bs4 import BeautifulSoup
from ..exceptions import *
from ..annotations import *

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

def getTokens(fpath, mentions=None, get_POS_tags=False, by_sentence=False, _token_types=[], _sentence_type=None):
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
        get_POS_tags :: Boolean flag to return POS tag information along
                        with token strings
        by_sentence  :: return lists of tokens, where each corresponds to a
                        single sentence as partitioned by cTAKES
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
        # get valid child nodes and sort by beginning index
        validated_nodes = _get_and_validate_children(soup, node_type, regex)
        sorted_nodes = _sort_by_position(validated_nodes, attr='begin')
        # pull out token and beginning index, store separately
        typed_tokens, typed_starts = [], []
        for node in sorted_nodes:
            token_string = node['normalizedForm']
            if get_POS_tags:
                try: token_pos = node['partOfSpeech']
                except KeyError: token_pos = None
                typed_tokens.append( (token_string, token_pos) )
            else:
                typed_tokens.append(token_string)
            typed_starts.append(int(node['begin']))
        tokens.append(typed_tokens)
        starts.append(typed_starts)

    # if getting by sentence, fetch and order all the tagged sentences
    if by_sentence:
        (sentence_node_type, sentence_regex) = _sentence_type
        # get sentence nodes and sort by beginning index
        validated_nodes = _get_and_validate_children(soup, sentence_node_type, sentence_regex)
        sorted_sentences = _sort_by_position(validated_nodes, attr='begin')
        # cast to Sentence objects
        sorted_sentences = [Sentence(bounds=(int(s['begin']), int(s['end']))) for s in sorted_sentences]
    
    ordered_tokens = []

    # starts_remaining tracks the start indices for the token types left
    # to empty; contains pairs of token type (index) and start indices
    starts_remaining = []
    for i in range(len(starts)):
        if len(starts[i]) > 0: starts_remaining.append((i,starts[i]))
    
    cur_mentions = []   # current list of overlapping mentions
    overlap_sofar = []  # tokens in the current overlap preceding the next mention
    in_mention = False  # are we currently in >0 mentions?

    if by_sentence:
        current_sentence = None

    while len(starts_remaining) > 0:
        # find the next token type from the text
        next_starts = [start[0] for (_,start) in starts_remaining]
        next_starts_ix = np.argmin(next_starts)
        next_tokentype = starts_remaining[next_starts_ix][0]
        # get the next token
        next_token = tokens[next_tokentype].pop(0)
        next_token_start = starts_remaining[next_starts_ix][1][0]

        # if still in one or more mentions, try to resolve them
        if in_mention:
            # check for completed mentions and add token appropriately
            in_mention = False
            for (before, m, after) in cur_mentions:
                if m.end > next_token_start:
                    m.text.append(next_token)
                    in_mention = True
                else:
                    after.append(next_token)

                # make sure no mentions are going outside a sentence
                if by_sentence and not current_sentence is None:
                    assert m.end <= current_sentence.end

            # if all mentions completed, flush them as a block
            if not in_mention:
                for (before, m, after) in cur_mentions:
                    m.text = ' '.join(m.text)
                    after.pop(-1) # the last token is spurious
                if by_sentence and not current_sentence is None:
                    current_sentence.tokens.append(cur_mentions)
                else:
                    ordered_tokens.append(cur_mentions)
                # and reset the overlap trackers
                cur_mentions, overlap_sofar = [], []

        # if in a sentence, try to resolve it
        if by_sentence and not current_sentence is None:
            if current_sentence.end <= next_token_start:
                ordered_tokens.append(current_sentence)
                current_sentence = None
        # if at the start of a sentence, load it in
        if by_sentence and len(sorted_sentences) > 0 and next_token_start >= sorted_sentences[0].begin:
            current_sentence = sorted_sentences.pop(0)

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
            if by_sentence and not current_sentence is None:
                current_sentence.tokens.append(next_token)
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
    if in_mention:
        for (before, m, after) in cur_mentions:
            m.text = ' '.join(m.text)
        if by_sentence and not current_sentence is None:
            current_sentence.tokens.append(cur_mentions)
        else:
            ordered_tokens.append(cur_mentions)

    # check if still have a sentence buffered
    if by_sentence and not current_sentence is None:
        ordered_tokens.append(current_sentence)
        current_sentence = None

    # flatten mentions and contexts
    output_tokens = _flatten_mention_spans(ordered_tokens)

    return output_tokens

def _get_and_validate_children(soup, node_type, validation_regex):
    candidate_nodes, validated_nodes = soup.findChildren(node_type), []
    for node in candidate_nodes:
        if matchesRegex(validation_regex, repr(node)): validated_nodes.append(node)
    return validated_nodes

def _sort_by_position(nodes, attr='begin'):
    node_sorter = { int(node[attr]): node for node in nodes }
    assert len(node_sorter) == len(nodes)  # no duplicate 'begin' indices
    indices, sorted_nodes = list(node_sorter.keys()), []
    indices.sort()
    for index in indices:
        sorted_nodes.append(node_sorter[index])
    return sorted_nodes

def _flatten_mention_spans(token_list):
    output_tokens = []
    for t in token_list:
        if type(t) == Sentence:
            t.tokens = _flatten_mention_spans(t.tokens)
            output_tokens.append(t)
        elif type(t) == list:
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
