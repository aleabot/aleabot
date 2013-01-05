#
# Copyright (C) 2012-2013 Aleabot
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


import alea.expr
import alea.util
import re

class AleabotSyntaxError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

def aleabot_parse(line):
    # The big ol' parser routine

    # Takes a string (something sent to the bot via PM) and returns it
    # in a format that is much simpler to process. Specifically, unless
    # this function throws an exception (AleabotSyntaxError) it
    # returns a tuple of one of the following forms:
    #   ('rollrequest', expressionlist, channelname) where
    #     - expressionlist is a list of expression objects
    #     - for public rolls, channelname is the name of the chat channel
    #       (without initial slash), for private rolls, channelname = ''
    #   ('helprequest')
    #   ('hellorequest')
    #   ('thanksrequest')
    #   ('wangrequest', playername)
    #     - playername is the name of the player (not yet resolved to user id)
    #   ('arrowrequest', playername)
    #     - playername is the name of the player (not yet resolved to user id)
    #   ('uneffectrequest', uneffectable)
    #     - uneffectable is an instance of class alea.util.Uneffectable
    #   ('nullrequest')

    # First step in parsing is lexing. This inner function takes the line
    # passed to aleabot_parse() and converts it into a list of tokens.
    # Each token is represented by a 1-element or 2-element tuple, where
    # the first element is the token name (a string) and the second is
    # an optional parameter.
    def lexer(line):
        digits = '0123456789'
        alphabetic = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        alphabetic += alphabetic.lower()
        namechars = alphabetic + digits + ' _'
        tokens = []
        pos = 0
        expect_name = False
        expect_name_ignore_slash = False
        # Normalize whitespace
        line = re.sub(r'\s+', ' ', line).strip()
        # Scan the line
        while pos < len(line):
            pos1 = pos
            c = line[pos1]
            pos += 1
            if c in alphabetic:
                pos2 = pos1 + 1
                while pos2 < len(line) and line[pos2] in alphabetic:
                    pos2 = pos2 + 1
                pos = pos2
                keyword = line[pos1:pos2].lower()
                if keyword == 'roll' or keyword == 'compute':
                    tokens.append(('rollcommand',))
                elif keyword == 'help':
                    tokens.append(('helpcommand',))
                elif keyword == 'hello' or keyword == 'hi' or keyword == 'hey':
                    tokens.append(('hellocommand',))
                elif keyword == 'thanks' or keyword == 'thank' or keyword == 'ty' or keyword == 'thx':
                    tokens.append(('thankscommand',))
                    expect_name = True
                elif keyword == 'wang':
                    tokens.append(('wangcommand',))
                    expect_name = True
                elif keyword == 'arrow':
                    tokens.append(('arrowcommand',))
                    expect_name = True
                elif keyword == 'uneffect':
                    tokens.append(('uneffectcommand',))
                    expect_name = True
                elif keyword == 'in':
                    tokens.append(('in',))
                    expect_name = True
                    expect_name_ignore_slash = True
                elif keyword == 'please':
                    tokens.append(('please',))
                elif keyword == 'and':
                    tokens.append(('listseparator',))
                elif keyword == 'd':
                    tokens.append(('dice','D'))
                else:
                    raise AleabotSyntaxError('unknown keyword')
            elif c in digits:
                while pos < len(line) and line[pos] in digits:
                    pos += 1
                value = int(line[pos1:pos])
                if pos < len(line) and alea.util.isunit(line[pos]):
                    value *= alea.util.getunit(line[pos])
                    pos += 1
                tokens.append(('number', value))
            elif c == '.' or c == '!' or c == '?':
                tokens.append(('sentenceend',))
                # note: sentenceend before end will be removed by a later step
            elif c == ',' or c == ';':
                tokens.append(('listseparator',))
            elif c == '(':
                tokens.append(('lparen',))
            elif c == ')':
                tokens.append(('rparen',))
            elif c == '+':
                tokens.append(('plusminus','+'))
            elif c == '-':
                tokens.append(('plusminus','-'))
            elif c == '*':
                if line[pos] == '*':
                    pos += 1
                    tokens.append(('pow','^'))
                else:
                    tokens.append(('muldiv','*'))
            elif c == '/':
                tokens.append(('muldiv','/'))
            elif c == '%':
                tokens.append(('muldiv','%'))
            elif c == '^':
                tokens.append(('pow','^'))
            elif c == '<' and pos < len(line) and line[pos] == '3':
                pos += 1
                tokens.append(('heart_or_smile',))
            elif c == ':':
                if pos < len(line) and line[pos] == '-':
                    pos += 1
                if pos < len(line) and line[pos] in (')', 'D'):
                    pos += 1
                    tokens.append(('heart_or_smile',))
                else:
                    raise AleabotSyntaxError('broken smile')
            else:
                raise AleabotSyntaxError("can't parse symbol: " + c)
            if expect_name:
                # channel name for rollrequest
                # player name for wangrequest and arrowrequest
                # effect name for uneffectrequest
                if expect_name_ignore_slash:
                    while pos < len(line) and line[pos].isspace():
                        pos += 1
                    if pos < len(line) and line[pos] == '/':
                        pos += 1
                pos_namestart = pos
                while pos < len(line) and line[pos] in namechars:
                    pos += 1
                name = line[pos_namestart:pos].strip()
                tokens.append(('name', name))
                expect_name = False
                expect_name_ignore_slash = False
            while pos < len(line) and line[pos].isspace():
                pos += 1
        tokens.append(('end',))
        return tokens
    # After the lexing is done, the tokens must be processed.
    # Some helper functions for that purpose follow.
    # Note: 'state' always refers to a state object that contains the list
    # of tokens (state.tokens) and the current token position (state.tokenpos).
    # The state object is persistent within an aleabot_parse call.
    def is_token(state,tok):
        return state.tokens[state.tokenpos][0] == tok
    def get_token_parameter(state):
        return state.tokens[state.tokenpos][1]
    def advance(state):
        state.tokenpos += 1
    # The recursive descent parser for the request syntax follows.
    # Each function implements a production rule.
    def parse_request(state):
        if is_token(state, 'please'):
            advance(state)
        if is_token(state, 'rollcommand'):
            advance(state)
            expressionlist = parse_expressionlist(state)
            if is_token(state, 'in'):
                advance(state)
                # Parse the channel name (don't check for authorization yet)
                if is_token(state, 'name'):
                    channel = get_token_parameter(state)
                    advance(state)
                    if is_token(state, 'end'):
                        return ('rollrequest', expressionlist, channel)
            elif is_token(state, 'end'):
                return ('rollrequest', expressionlist, '')
            raise AleabotSyntaxError('unable to parse roll request')
        elif is_token(state, 'helpcommand'):
            advance(state)
            if is_token(state, 'end'):
                return ('helprequest',)
            raise AleabotSyntaxError('unable to parse help request')
        elif is_token(state, 'hellocommand'):
            advance(state)
            if is_token(state, 'end'):
                return ('hellorequest',)
            raise AleabotSyntaxError('unable to parse hello request')
        elif is_token(state, 'thankscommand'):
            advance(state)
            if is_token(state, 'name'):
                playername = get_token_parameter(state)
                if playername == '' or playername.lower() == 'you' or playername.lower() == 'to you' or playername == 'u' or playername.lower() == 'aleabot' or playername.lower() == 'alea':
                    advance(state)
                    if is_token(state, 'end'):
                        return ('thanksrequest',)
            raise AleabotSyntaxError('unable to parse thanks request')
        elif is_token(state, 'wangcommand'):
            advance(state)
            if is_token(state, 'name'):
                playername = get_token_parameter(state)
                if playername.lower() == 'me':
                    playername = ''
                advance(state)
                if is_token(state, 'end'):
                    return ('wangrequest', playername)
            raise AleabotSyntaxError('unable to parse wang request')
        elif is_token(state, 'arrowcommand'):
            advance(state)
            if is_token(state, 'name'):
                playername = get_token_parameter(state)
                if playername.lower() == 'me':
                    playername = ''
                advance(state)
                if is_token(state, 'end'):
                    return ('arrowrequest', playername)
            raise AleabotSyntaxError('unable to parse arrow request')
        elif is_token(state, 'uneffectcommand'):
            advance(state)
            if is_token(state, 'name'):
                effectname = get_token_parameter(state)
                advance(state)
                if is_token(state, 'end'):
                    return ('uneffectrequest', alea.util.Uneffectable(effectname))
            raise AleabotSyntaxError('unable to parse uneffect request')
        elif is_token(state, 'end'):
            return ('nullrequest',)
        raise AleabotSyntaxError('unable to parse request')
    def parse_expressionlist(state):
        exprlist = [parse_expression(state)]
        while is_token(state, 'listseparator'):
            advance(state)
            exprlist.append(parse_expression(state))
        return exprlist
    def parse_expression(state):
        return parse_sum(state)
    def parse_sum(state):
        if is_token(state, 'plusminus'):
            op = get_token_parameter(state)
            advance(state)
            subexpr_a = parse_product(state)
            expr = alea.expr.UnaryExpr(subexpr_a, op)
        else:
            expr = parse_product(state)
        while is_token(state, 'plusminus'):
            op = get_token_parameter(state)
            advance(state)
            subexpr_a = expr
            subexpr_b = parse_product(state)
            expr = alea.expr.BinaryExpr(subexpr_a, subexpr_b, op)
        return expr
    def parse_product(state):
        expr = parse_power(state)
        while is_token(state, 'muldiv'):
            op = get_token_parameter(state)
            advance(state)
            subexpr_a = expr
            subexpr_b = parse_power(state)
            expr = alea.expr.BinaryExpr(subexpr_a, subexpr_b, op)
        return expr
    def parse_power(state):
        expr = parse_diceterm(state)
        while is_token(state, 'pow'):
            op = get_token_parameter(state)
            advance(state)
            subexpr_a = expr
            subexpr_b = parse_power(state)  # <-- recurse to implement the right binding power operator
            expr = alea.expr.BinaryExpr(subexpr_a, subexpr_b, op)
        return expr
    def parse_diceterm(state):
        if is_token(state, 'dice'):
            op = get_token_parameter(state)
            advance(state)
            subexpr_a = parse_simpleexpression(state)
            # Treat as 1dX
            return alea.expr.BinaryExpr(alea.expr.NumberExpr(1), subexpr_a, op)
        else:
            expr = parse_simpleexpression(state)
            if is_token(state, 'dice'): # non-binding operator => don't iterate here
                op = get_token_parameter(state)
                advance(state)
                subexpr_a = expr
                subexpr_b = parse_simpleexpression(state)
                expr = alea.expr.BinaryExpr(subexpr_a, subexpr_b, op)
            return expr
    def parse_simpleexpression(state):
        if is_token(state, 'number'):
            value = get_token_parameter(state)
            advance(state)
            return alea.expr.NumberExpr(value)
        elif is_token(state, 'lparen'):
            advance(state)
            expr = parse_expression(state)
            if is_token(state, 'rparen'):
                advance(state)
                return expr
        raise AleabotSyntaxError('unable to parse expression')
    # Top level aleabot_parse() code
    state = alea.util.Expando()
    state.tokens = lexer(line)
    # if the list of tokens ends with 'heart_or_smile';'end', remove 'heart_or_smile'
    if len(state.tokens) >= 2 and state.tokens[-2][0] == 'heart_or_smile':
        state.tokens.pop(-2)
    # if the list of tokens ends with 'sentenceend';'end', remove 'sentenceend'
    if len(state.tokens) >= 2 and state.tokens[-2][0] == 'sentenceend':
        state.tokens.pop(-2)
    state.tokenpos = 0
    return parse_request(state)


if __name__ == '__main__':
    import readline
    rng = alea.rng.RNG()
    while True:
        s = raw_input('--> ')
        t = None
        try:
            t = aleabot_parse(s)
        except AleabotSyntaxError as err:
            print('Syntax error: ' + str(err))
            t = None
        print repr(t)
        if t is not None and t[0] == 'rollrequest':
            for i in range(0, len(t[1])):
                print 'Expression: ' + str(t[1][i])
                try:
                    print 'Eval: ' + str(t[1][i].eval(rng, alea.expr.DiceCounter(0)))
                    print 'Classify dice: ' + str(t[1][i].classify_dice())
                except alea.expr.AleabotEvalError as err:
                    print 'error: ' + str(err)
            print 'Channel: ' + str(t[2])
        if t is not None and t[0] == 'uneffectrequest':
            print 'Input effect name: ' + t[1].inputname()
            print 'Matching effect count: '  + str(t[1].count())
            print 'Matching effect ids: '  + ', '.join(str(x) for x in t[1].effect_ids())
            print 'Matching effect names: '  + ', '.join(t[1].effect_names())

