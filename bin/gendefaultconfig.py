#!/usr/bin/env python

# Import directory magic
from __future__ import absolute_import
import os, sys
scriptpath = os.path.abspath(__file__)
basepath = os.path.realpath(os.path.join(os.path.dirname(scriptpath), '..'))
sys.path.append(os.path.join(basepath, 'src/'))

# "Actual" imports
import optparse
import alea.config
import alea.rng

if __name__ == '__main__':
    usage = 'Usage: %prog'
    optionparser = optparse.OptionParser(usage=usage)
    optionparser.add_option('-s', '--stdout', dest='stdout',
            action='store_true', default=False,
            help='Send output to stdout instead of aleabot.conf.default')

    (options, args) = optionparser.parse_args()

    config = alea.config.AleabotConfig(alea.rng.RNG())
    config.load_defaults()
    if options.stdout:
        config.write(sys.stdout)
    else:
        outfile = file(os.path.join(basepath, 'aleabot.conf.default'), 'w')
        config.write(outfile)
        outfile.close()

