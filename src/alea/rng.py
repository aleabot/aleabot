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
    def __init__(self):
        try:
            self._source = file(rngsource)
        except IOError:
            print 'Unable to open ' + rngsource + ' - using os.urandom() instead'
            self._source = None
        self._unicorn = 0  # Originally called _uniform but I like this typo
        self._modulus = 1

    def _readsource(self, required_modulus):
        # Read random bytes from the source until our modulus is
        # at least required_modulus
        if self._modulus < required_modulus:
            # Note: the following formula sometimes causes too many bytes to be read
            # (which is not a problem), but never too few.
            bytes_to_read = max(ceildiv(intlog2(ceildiv(required_modulus, self._modulus)) + 1, 8), 16)
            #print('Reading ' + str(bytes_to_read) + ' bytes from random source')
            if self._source:
                new_data = self._source.read(bytes_to_read)
            else:
                new_data = os.urandom(bytes_to_read)
            assert(len(new_data) == bytes_to_read)
            for i in range(0, bytes_to_read):
                self._unicorn = (self._unicorn << 8) | ord(new_data[i])
            self._modulus = (self._modulus << (8*bytes_to_read))
            assert(self._modulus >= required_modulus)
            assert(self._unicorn >= 0)
            assert(self._unicorn < self._modulus)

    def get(self, minvalue, maxvalue, n):
        # Get n random integers between minvalue and maxvalue, inclusive.
        # Returns a list (of length n) of integers.
        assert(minvalue <= maxvalue)
        assert(n >= 0)
        if minvalue == maxvalue:
            return [minvalue]*n
        l = list()
        range_size = maxvalue - minvalue + 1

        # See http://mathforum.org/library/drmath/view/65653.html
        for i in range(0, n):
            while True:
                self._readsource(range_size)
                q = self._modulus // range_size
                if self._unicorn >= range_size*q:
                    self._unicorn -= range_size*q
                    self._modulus -= range_size*q
                    continue
                l.append(self._unicorn % range_size + minvalue)
                self._unicorn = self._unicorn // range_size
                self._modulus = q
                break
        return l

    def get_one(self, minvalue, maxvalue):
        return self.get(minvalue, maxvalue, 1)[0]

class RNG_xkcd(object):
    def __init__(self):
        pass

    def get(self, minvalue, maxvalue, n):
        assert(minvalue <= maxvalue)
        value = 4  # chosen by fair dice roll.
                   # guaranteed to be random.
        value = max(min(value, maxvalue), minvalue)
        return [value]*n

    def get_one(self, minvalue, maxvalue):
        return self.get(minvalue, maxvalue, 1)[0]
