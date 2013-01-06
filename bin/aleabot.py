#!/usr/bin/env python

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


# Import directory magic
from __future__ import absolute_import
import os, sys
scriptpath = os.path.abspath(__file__)
basepath = os.path.realpath(os.path.join(os.path.dirname(scriptpath), '..'))
sys.path.append(os.path.join(basepath, 'src/'))
sys.path.append(os.path.join(basepath, 'pykol/src/'))

# "Actual" imports
import alea.AleabotFilter
import alea.config
import alea.rng
from kol.bot.Bot import Bot
from kol.bot import BotManager
from kol.manager import FilterManager
from kol.util import Report

if __name__ == '__main__':
    # Create a random number generator
    rng = alea.rng.RNG()

    # Load the config file
    config = alea.config.AleabotConfig(rng)
    config.load(basepath)

    # Set up console and file logging
    Report.setOutputLevel(config.get('report_level'))
    log_file = config.get('log_file')
    if log_file != '':
        log_file_full_path = os.path.join(basepath, log_file)
        Report.registerLog(os.path.dirname(log_file_full_path),
                os.path.basename(log_file_full_path),
                ['*'],
                config.get('log_level'))

    # Create and register our custom bot filter
    alea.AleabotFilter.init(rng, config)
    FilterManager.registerFilterForEvent(alea.AleabotFilter, "botProcessChat")
    FilterManager.registerFilterForEvent(alea.AleabotFilter, "botProcessKmail")
    FilterManager.registerFilterForEvent(alea.AleabotFilter, "botEndCycle")
    FilterManager.registerFilterForEvent(alea.AleabotFilter, "botPreLogin")

    # Start the bot manager
    BotManager.init()

    # Create and run the bot
    params = {}
    params['doWork:chat'] = True
    params['doWork:kmail'] = True
    params['userName'] = config.get('username')
    params['userPassword'] = config.get('password')
    params['timeToSleep'] = config.get('time_to_sleep')
    b = Bot(params)
    BotManager.registerBot(b)
    BotManager.runBots()

