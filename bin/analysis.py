#!/usr/bin/env python

# Import directory magic
from __future__ import absolute_import
import os, sys
scriptpath = os.path.abspath(__file__)
basepath = os.path.realpath(os.path.join(os.path.dirname(scriptpath), '..'))
sys.path.append(os.path.join(basepath, 'src/'))

# "Actual" imports
import math
import re
import optparse
import alea.expr
import alea.parser
import alea.rng
import alea.util

class AutocorrelationCounter(object):
    def __init__(self, maxlag):
        self._maxlag = maxlag
        self._n = 0
        self._first = []
        self._last = []
        self._sum = 0
        self._corsum = [0]*(maxlag+1)
        self._min = None
        self._max = None
    def add(self, x):
        self._n += 1
        j = self._maxlag
        n = self._n
        if n <= j+1:
            self._first.append(x)
        self._last.insert(0, x)
        if n > j+1:
            self._last.pop()
        self._sum += x
        for k in range(0, min(j+1, n)):
            self._corsum[k] += self._last[k] * x
        if self._min is None or self._min > x:
            self._min = x
        if self._max is None or self._max < x:
            self._max = x
    def count(self):
        return self._n
    def min(self):
        return self._min
    def max(self):
        return self._max
    def maxlag(self):
        return self._maxlag
    def mean(self):
        n = self._n
        if n >= 1:
            return self._sum / float(n)
        else:
            return 0.0
    def variance(self):
        n = self._n
        if n >= 2:
            m = self._sum / float(n)
            return float(n) / float(n-1) * (self._corsum[0] / float(n) - m * m)
        else:
            return 0.0
    def stddev(self):
        v = self.variance()
        if v >= 0.0:  # Mathematically always the case, but floating point
            return math.sqrt(v)
        else:
            return 0.0
    def autocovariance(self, k):
        if k < 0 or k > self._maxlag:
            return None
        n = self._n
        if n >= k+1:
            m = self._sum / float(n)
            firstsum = sum(self._first[0:k])
            lastsum = sum(self._last[0:k])
            return 1 / float(n-k) * (self._corsum[k] - m * (2 * self._sum - firstsum - lastsum)) + m*m
        else:
            return 0.0
    def autocorrelation(self, k):
        if k < 0 or k > self._maxlag:
            return None
        autocov = self.autocovariance(k)
        v = self.variance()
        if v > 0.0:
            return autocov / v
        else:
            return None
    def debug(self):
        print("maxlag: " + str(self._maxlag))
        print("n: " + str(self._n))
        print("first: " + ", ".join([str(x) for x in self._first]))
        print("last: " + ", ".join([str(x) for x in self._last]))
        print("sum: " + str(self._sum))
        print("corsum: " + ", ".join([str(x) for x in self._corsum]))
        print("min: " + str(self._min))
        print("max: " + str(self._max))
    def report(self):
        print("count = " + str(self.count()))
        print("min = " + str(self.min()))
        print("max = " + str(self.max()))
        print("mean = " + str(self.mean()))
        print("variance = " + str(self.variance()))
        print("stddev = " + str(self.stddev()))
        for k in range(0, self.maxlag()+1):
            print("autocovariance(" + str(k) + ") = " + str(self.autocovariance(k)))
        for k in range(0, self.maxlag()+1):
            print("autocorrelation(" + str(k) + ") = " + str(self.autocorrelation(k)))

class Histogram(object):
    def __init__(self, minlimit, maxlimit, buckets):
        self._n = 0
        self._minlimit = minlimit
        self._maxlimit = maxlimit
        self._rangesize = maxlimit - minlimit
        self._k = buckets
        self._buckets = [0]*buckets
    def add(self, x):
        self._n += 1
        if x >= self._minlimit and x < self._maxlimit:
            bucket = (self._k * (x - self._minlimit)) // (self._rangesize)
            self._buckets[bucket] += 1
    def bucketcount(self):
        return self._k
    def bucketrange(self, bucket):
        assert(bucket >= 0 and bucket < self._k)
        # lower end, inclusive
        lower = self._minlimit + alea.util.ceildiv(bucket * self._rangesize, self._k)
        # upper end, exclusive
        upper = self._minlimit + alea.util.ceildiv((bucket+1) * self._rangesize, self._k)
        return (lower, upper)
    def frequency_absolute(self, bucket):
        assert(bucket >= 0 and bucket < self._k)
        return self._buckets[bucket]
    def frequency_relative(self, bucket):
        assert(bucket >= 0 and bucket < self._k)
        return float(self._buckets[bucket]) / self._n
    def report(self):
        for bucket in range(0, self.bucketcount()):
            lower, upper = self.bucketrange(bucket)
            freq_abs = self.frequency_absolute(bucket)
            freq_rel = self.frequency_relative(bucket)
            if lower < upper:
                print "Bucket %d-%d: %d (%f%%)" % (lower, upper-1, freq_abs, freq_rel*100.0)
            else:
                assert(freq_abs == 0)

class BadUsageError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

def test_expression(expr, rng, options):
    # Create the autocorrelation counter for basic statistical data
    if options.maxlag < 0:
        raise BadUsageError('Maxlag must be at least 0')
    ac = AutocorrelationCounter(options.maxlag)

    # Create a histogram object if wanted
    histogram = None
    if options.histogram != '':
        match = re.match('([0-9]+),([0-9]+),([0-9]+)', options.histogram)
        if match:
            minlimit = int(match.group(1))
            maxlimit = int(match.group(2)) + 1 # account for exclusive max limit
            buckets = int(match.group(3))
            if minlimit >= maxlimit:
                raise BadUsageError('Histogram min limit must be less than max limit')
            if buckets < 1:
                raise BadUsageError('Number of histogram buckets must be at least 1')
            histogram = Histogram(minlimit, maxlimit, buckets)
        else:
            raise BadUsageError('Histogram parameters must be given in the form minlimit,maxlimit,buckets')

    # Roll the dice!
    print 'Rolling ' + str(expr) + ' ' + str(options.samples) + ' times gives...'
    dicecounter = alea.expr.DiceCounter(0)
    for j in range(0, options.samples):
        x = expr.eval(rng, dicecounter)
        ac.add(x)
        if histogram:
            histogram.add(x)

    # Report results
    ac.report()
    if histogram:
        print 'Histogram:'
        histogram.report()

def test_request(request, rng, options):
    if request[0] == 'rollrequest':
        for i in range(0, len(request[1])):
            expr = request[1][i]
            if i != 0:
                print ('='*72)
            test_expression(expr, rng, options)
    else:
        raise BadUsageError('Roll request expected')


if __name__ == '__main__':
    usage = 'Usage example: %prog roll 1D100000'
    optionparser = optparse.OptionParser(usage=usage)
    optionparser.add_option('-s', '--samples', dest='samples',
            type='int', action='store',
            help='Generate N random samples',
            metavar='N', default=100000)
    optionparser.add_option('-j', '--maxlag', dest='maxlag',
            type='int', action='store',
            help='Compute autocorrelation up to lag of MAXLAG',
            metavar='MAXLAG', default=20)
    optionparser.add_option('-H', '--histogram', dest='histogram',
            type='string', action='store',
            help='Create a histogram between A and B with K buckets',
            metavar='A,B,K', default='')

    (options, args) = optionparser.parse_args()

    bad_usage = False
    try:
        request = alea.parser.aleabot_parse(' '.join(args))
        rng = alea.rng.RNG()
        test_request(request, rng, options)
    except alea.parser.AleabotSyntaxError as e:
        print('Unable to parse request!')
        print('Error: ' + str(e))
        bad_usage = True
    except alea.expr.AleabotEvalError as e:
        print('Unable to evaluate expression!')
        print('Error: ' + str(e))
    except BadUsageError as e:
        print('Invalid options!')
        print('Error: ' + str(e))
    if bad_usage:
        optionparser.print_help()

