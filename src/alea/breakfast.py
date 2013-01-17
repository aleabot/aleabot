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


"""
Robot breakfast
"""


import kol.Error as Error
from kol.manager import FilterManager
from kol.manager import PatternManager
from kol.request.GenericRequest import GenericRequest
from kol.request.MeatBushRequest import MeatBushRequest
from kol.request.MeatOrchidRequest import MeatOrchidRequest
from kol.request.MeatTreeRequest import MeatTreeRequest
from kol.util import Report
from kol.util import ParseResponseUtils


class HippyProduceStandRequest(GenericRequest):
    "Goes to the hippy produce stand to retrieve daily meat."
    def __init__(self, session):
        super(HippyProduceStandRequest, self).__init__(session)
        self.url = session.serverURL + 'store.php?whichstore=h'

    def parseResponse(self):
        if len(self.responseText) == 0:
            raise Error.Error('You cannot visit that store yet.', Error.INVALID_LOCATION)
        self.responseData['meat'] = ParseResponseUtils.parseMeatGainedLost(self.responseText)


def breakfast(session):
    Report.info('bot', 'Start of breakfast.')

    meatGained = 0

    Report.info('bot', 'Visiting hippy produce stand.')
    try:
        req = HippyProduceStandRequest(session)
        response = req.doRequest()
        meatGained += response['meat']
    except Error.Error as err:
        Report.error('bot', 'Error while visiting hippy produce stand: ' + str(err))

    Report.info('bot', 'Visiting potted meat bush.')
    try:
        req = MeatBushRequest(session)
        response = req.doRequest()
        meatGained += response['meat']
    except Error.Error as err:
        Report.error('bot', 'Error while visiting potted meat bush: ' + str(err))

    Report.info('bot', 'Visiting exotic hanging meat orchid.')
    try:
        req = MeatOrchidRequest(session)
        response = req.doRequest()
        meatGained += response['meat']
    except Error.Error as err:
        Report.error('bot', 'Error while visiting exotic hanging meat orchid: ' + str(err))

    Report.info('bot', 'Visiting potted meat tree.')
    try:
        req = MeatTreeRequest(session)
        response = req.doRequest()
        meatGained += response['meat']
    except Error.Error as err:
        Report.error('bot', 'Error while visiting potted meat tree: ' + str(err))

    Report.info('bot', 'End of breakfast. Meat gained: ' + str(meatGained))

