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


import alea.rng
import alea.util

class AleabotEvalError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class ResultCountExceededError(AleabotEvalError):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class DiceCountExceededError(AleabotEvalError):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class DicelessDisallowedError(AleabotEvalError):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class D1DisallowedError(AleabotEvalError):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class DiceCounter(object):
    def __init__(self, limit):
        self.count = 0
        self.limit = limit
    def add(self, n):
        self.count = self.count + n
        if self.count > self.limit and self.limit != 0:
            raise DiceCountExceededError('More than ' + str(self.limit) + ' dice used')

# Operator levels for Aleabot expressions:
#   0 - addition, subtraction
#   1 - multiplication, division, remainder
#   2 - exponentiation
#   3 - dice operator
#   4 - atoms (numbers)

class BinaryExpr(object):
    # Operator levels, used for formatting
    oplevel = {
            # 'operator': (
            #     operator level,
            #     left operand needs parentheses if below this level,
            #     right operand needs parentheses if below this level,
            # )
            '+': (0, 0, 1),
            '-': (0, 0, 1),
            '*': (1, 1, 2),
            '/': (1, 1, 2),
            '%': (1, 1, 2),
            '^': (2, 3, 2),
            'D': (3, 4, 4),
            'S': (3, 4, 4),
    }

    # Maximum number of bits in the result of an exponentiation operation
    # (to prevent excessive computation times)
    exponentiation_max_bits = 1024

    def __init__(self,a,b,op):
        assert(op in BinaryExpr.oplevel)
        self.a = a
        self.b = b
        self.op = op

    def eval(self, rng, dicecounter, maxresults):
        if maxresults < 1:
            raise ResultCountExceededError('result count exceeded')
        aval = self.a.eval(rng, dicecounter, 1)[0]
        bval = self.b.eval(rng, dicecounter, 1)[0]
        if self.op == '+':
            return [aval + bval]
        elif self.op == '-':
            return [aval - bval]
        elif self.op == '*':
            return [aval * bval]
        elif self.op == '/':
            if bval == 0:
                raise AleabotEvalError("doesn't compute: (" + str(aval) + ")/(" + str(bval) + ")")
            return [aval // bval]  # integer division only
        elif self.op == '%':
            if bval == 0:
                raise AleabotEvalError("doesn't compute: (" + str(aval) + ")%(" + str(bval) + ")")
            return [aval % bval]
        elif self.op == '^':
            if bval < 0:
                raise AleabotEvalError("doesn't compute: (" + str(aval) + ")^(" + str(bval) + ")")
            if alea.util.intlog2(abs(aval)) * bval > BinaryExpr.exponentiation_max_bits:
                raise AleabotEvalError("exponentiation limit exceeded: (" + str(aval) + ")^(" + str(bval) + ")")
            return [aval ** bval]  # note: returns 1 for aval == bval == 0
        elif self.op == 'D':
            if aval < 0 or bval <= 0:
                raise AleabotEvalError("doesn't compute: (" + str(aval) + ")D(" + str(bval) + ")")
            dicecounter.add(aval)
            return [alea.util.roll(rng, aval, bval)]
        elif self.op == 'S':
            if self.a.classify_dice() != 0 or self.b.classify_dice() != 0:
                raise AleabotEvalError("operands of S operator must be diceless")
            if aval < 0 or bval <= 0 or aval > bval:
                raise AleabotEvalError("doesn't compute: (" + str(aval) + ")S(" + str(bval) + ")")
            if maxresults < aval:
                raise ResultCountExceededError('result count exceeded')
            return alea.util.shuffle(rng, aval, bval) 



    def classify_dice(self):
        # Returns 0 if expression is diceless (no 'd'/'s' operator),
        # returns 1 if all dice are D1s, returns 2 otherwise
        classify_a = self.a.classify_dice()
        classify_b = self.b.classify_dice()
        if self.op == 'D' or self.op == 'S':
            if classify_a <= 1 and classify_b <= 1 and self.b.eval(alea.rng.RNG_xkcd(), DiceCounter(0), 1) == 1:
                return 1
            else:
                return 2
        else:
            return max(classify_a, classify_b)

    def format(self, paren_if_level_below):
        level = BinaryExpr.oplevel[self.op][0]
        level_a = BinaryExpr.oplevel[self.op][1]
        level_b = BinaryExpr.oplevel[self.op][2]
        if level < paren_if_level_below:
            return '(' + self.a.format(level_a) + self.op + self.b.format(level_b) + ')'
        else:
            return self.a.format(level_a) + self.op + self.b.format(level_b)

    def __str__(self):
        return self.format(0)

class UnaryExpr(object):
    oplevel = {
            # 'operator': (
            #     operator level,
            #     operand needs parentheses if below this level,
            # )
            '+': (0, 1),
            '-': (0, 1),
    }

    def __init__(self,a,op):
        assert(op in UnaryExpr.oplevel)
        self.a = a
        self.op = op

    def eval(self, rng, dicecounter, maxresults):
        if maxresults < 1:
            raise ResultCountExceededError('result count exceeded')
        aval = self.a.eval(rng, dicecounter, 1)[0]
        if self.op == '+':
            return [aval]
        elif self.op == '-':
            return [-aval]

    def classify_dice(self):
        return self.a.classify_dice()

    def format(self, paren_if_level_below):
        level = UnaryExpr.oplevel[self.op][0]
        level_a = UnaryExpr.oplevel[self.op][1]
        if level < paren_if_level_below:
            return '(' + self.op + self.a.format(level_a) + ')'
        else:
            return self.op + self.a.format(level_a)

    def __str__(self):
        return self.format(0)

class NumberExpr(object):
    def __init__(self,value):
        self.value = value

    def eval(self, rng, dicecounter, maxresults):
        if maxresults < 1:
            raise ResultCountExceededError('result count exceeded')
        return [self.value]

    def classify_dice(self):
        return 0

    def format(self, paren_if_level_below):
        return alea.util.format_with_unit(self.value)

    def __str__(self):
        return self.format(0)

def aleabot_eval(exprlist, public, rng, aleabot_config):
    # Verify d1/diceless limit
    if public:
        allow_diceless = aleabot_config.get('allow_diceless_public')
        allow_d1 = aleabot_config.get('allow_d1_public')
    else:
        allow_diceless = aleabot_config.get('allow_diceless_private')
        allow_d1 = aleabot_config.get('allow_d1_private')
    if (not allow_diceless) or (not allow_d1):
        for expr in exprlist:
            classify = expr.classify_dice()
            if not allow_diceless and classify == 0:
                raise DicelessDisallowedError('Diceless roll not allowed')
            if not allow_d1 and classify == 1:
                raise D1DisallowedError('D1 roll not allowed')
    # Get result count limit. If <= 0, set to practically unlimited.
    result_count_max = aleabot_config.get('result_count_max')
    if result_count_max <= 0:
        result_count_max = 0xDEADBEEF  # Limited by meat. Wait, what?!
    # Roll (and at the same time verify result count / dice limits)
    dice_per_expression_max = aleabot_config.get('dice_per_expression_max')
    all_results = []
    for expr in exprlist:
        results = expr.eval(rng,
                DiceCounter(dice_per_expression_max),
                result_count_max)
        result_count_max -= len(results)
        all_results.extend(results)
    return all_results
