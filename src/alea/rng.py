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


import os
from alea.util import intlog2, ceildiv

# Must be /dev/urandom or /dev/random (think hard and know the implications
# before choosing the latter)
rngsource = '/dev/urandom'

# If rngsource can't be opened (e.g. on Windows), we use os.urandom() instead.
# We don't use os.urandom() on POSIX since its implementation re-opens and
# closes the urandom device on each call. This makes at least analysis.py
# slower than it should be.

class RNG(object):
    # class invariant (CI):
    # self._modulus >= 1 and self._unicorn is a uniformly distributed integer
    # from the set {0, ..., self._modulus-1}

    def __init__(self):
        try:
            self._source = file(rngsource)
        except IOError:
            print 'Unable to open ' + rngsource + ' - using os.urandom() instead'
            self._source = None
        self._unicorn = 0  # Originally called _uniform but I like this typo
        self._modulus = 1
        # CI holds here

    def _readsource(self, required_modulus):
        # Read random bytes from the source until our modulus is
        # at least required_modulus

        # CI holds here
        if self._modulus < required_modulus:
            # Note: the following formula sometimes causes too many bytes to be read
            # (which is not a problem), but never too few.
            bytes_to_read = max(ceildiv(intlog2(ceildiv(required_modulus, self._modulus)) + 1, 8), 16)
            #print('Reading ' + str(bytes_to_read) + ' bytes from random source')
            if self._source:
                new_data = self._source.read(bytes_to_read)
            else:
                new_data = os.urandom(bytes_to_read)
            # both functions should always return exactly bytes_to_read bytes
            assert(len(new_data) == bytes_to_read)

            for i in range(0, bytes_to_read):
                self._unicorn = (self._unicorn << 8) | ord(new_data[i])
            self._modulus = (self._modulus << (8*bytes_to_read))

            # CI holds here again

            assert(self._modulus >= required_modulus)
            assert(self._unicorn >= 0)
            assert(self._unicorn < self._modulus)

    def get(self, minvalue, maxvalue):
        # Get a random integer between minvalue and maxvalue, inclusive.

        # CI holds here

        assert(minvalue <= maxvalue)
        if minvalue == maxvalue:
            return minvalue
        range_size = maxvalue - minvalue + 1

        # See http://mathforum.org/library/drmath/view/65653.html
        while True:
            # CI holds here
            self._readsource(range_size)
            # CI holds here
            q = self._modulus // range_size
            if self._unicorn >= range_size*q:
                # Bad roll. Remove the unusable entropy and retry
                self._unicorn -= range_size*q
                self._modulus -= range_size*q
                # CI holds here
                continue

            # else, self._unicorn < range_size*q
            # which means that self._unicorn is distributed uniformly between
            # 0 and range_size*q-1 (both inclusive)
            # which means that if you divide self._unicorn by range_size,
            # the remainder is distributed uniformly between 0 and range_size-1
            # (both inclusive), the integer quotient is distributed uniformly
            # between 0 and q-1 (both inclusive), and the quotient and the
            # remainder are stochastically independent.

            value = self._unicorn % range_size
            self._unicorn = self._unicorn // range_size
            self._modulus = q
            # CI holds here
            return value + minvalue

class RNG_xkcd(object):
    def get(self, minvalue, maxvalue):
        assert(minvalue <= maxvalue)
        value = 4  # chosen by fair dice roll.
                   # guaranteed to be random.
        return max(min(value, maxvalue), minvalue)

