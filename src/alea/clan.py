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


import re
import time
import kol.Error as Error
from kol.request.GenericRequest import GenericRequest
from kol.request.UserProfileRequest import UserProfileRequest

class ClanRequestError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class Clan(object):
    def __init__(self, clanId, clanName):
        self._clanId = int(clanId)
        self._clanName = str(clanName)

    def valid(self):
        return self._clanId != 0 and self._clanName != ''

    def id(self):
        return self._clanId

    def name(self):
        return self._clanName

    def __repr__(self):
        return '(Clan id=' + repr(self._clanId) + ' name=' + repr(self._clanName) + ')'

    def __str__(self):
        return self._clanName

class WhitelistsRequest(GenericRequest):
    def __init__(self, session):
        super(WhitelistsRequest, self).__init__(session)
        self.url = session.serverURL + 'clan_signup.php'
        self.requestData['pwd'] = session.pwd

    def parseResponse(self):
        self.responseData['whitelists'] = {}
        match = re.search(r'<select name=whichclan>((<option value=[0-9]+>[^<>]*</option>)*)</select>', self.responseText)
        if match:
            for option_match in re.finditer(r'<option value=([0-9]+)>([^<>]*)</option>', match.group(1)):
                clanId = int(option_match.group(1))
                clanName = option_match.group(2)
                clan = Clan(clanId, clanName)
                self.responseData['whitelists'][clanId] = clan

class ClanSignupRequest(GenericRequest):
    def __init__(self, session, clan):
        super(ClanSignupRequest, self).__init__(session)
        self.url = session.serverURL + 'showclan.php'
        self.requestData['pwd'] = session.pwd
        self.requestData['action'] = 'joinclan'
        self.requestData['ajax'] = ''
        self.requestData['confirm'] = 'on'
        self.requestData['whichclan'] = clan.id()

    def parseResponse(self):
        if re.search(r'<img src="[^<>"]*/clanhalltop\.gif" width=[0-9]+ height=[0-9]+>', self.responseText):
            self.responseData['result'] = 'accepted'
        elif re.search(r'<td>You have submitted a request to join <b>[^<>]*</b><p>You will receive a message from the clan leader when your request is accepted \(or rejected\.\)</td>', self.responseText):
            self.responseData['result'] = 'pending'
        elif re.search(r'<td>This clan is not accepting admissions right now\.</td>', self.responseText):
            self.responseData['result'] = 'rejected'
        else:
            self.responseData['result'] = 'failed'

class ClanLeaveRequest(GenericRequest):
    def __init__(self, session):
        super(ClanLeaveRequest, self).__init__(session)
        self.url = session.serverURL + 'clan_members.php'
        self.requestData['pwd'] = session.pwd
        self.requestData['action'] = 'leaveclan'
        self.requestData['ajax'] = ''
        self.requestData['confirm'] = 'on'

class ClanState(object):
    def __init__(self):
        self._session = None
        self._my_clan = Clan(0, '')
        self._my_whitelists = {}
        self._state_valid = False
        self._state_valid_since = 0

    def set_session(self, session):
        self._session = session

    def verify_session(self):
        if self._session is None:
            raise ClanRequestError('No session established')
        if not self._session.isConnected:
            raise ClanRequestError('Session is not connected')
        return self._session

    def reload(self):
        self._state_valid = False
        try:
            session = self.verify_session()
            self._my_clan = self.player_clan(session.userId)
            req = WhitelistsRequest(session)
            response = req.doRequest()
            self._my_whitelists = response['whitelists']
            self._state_valid = True
            self._state_valid_since = time.time()
        except Error.Error, inst:
            raise ClanRequestError('failed to update clan state')

    def update(self, reload_time):
        if (not self._state_valid) or (reload_time > 0 and self._state_valid_since + reload_time <= time.time()):
            self.reload()
            return True
        return False

    def my_clan(self):
        if not self._state_valid:
            self.reload()
        return self._my_clan

    def my_whitelists(self):
        if not self._state_valid:
            self.reload()
        return self._my_whitelists.values()

    def have_whitelist(self, clan):
        if not self._state_valid:
            self.reload()
        return clan.id() in self._my_whitelists

    def player_clan(self, userId):
        try:
            session = self.verify_session()
            req = UserProfileRequest(session, userId)
            response = req.doRequest()
            if 'clanId' in response and 'clanName' in response:
                return Clan(response['clanId'], response['clanName'])
            else:
                return Clan(0, '')
        except (Error.Error, AttributeError):
            raise ClanRequestError('failed to fetch clan name from user profile')

    def switch(self, clan):
        if not self._state_valid:
            self.reload()
        try:
            if clan.id() == self._my_clan.id():
                return 'accepted'
            elif clan.id() == 0:
                session = self.verify_session()
                req = ClanLeaveRequest(session)
                response = req.doRequest()
                self._my_clan = clan
                return 'accepted'
            else:
                session = self.verify_session()
                req = ClanSignupRequest(session, clan)
                response = req.doRequest()
                if response['result'] == 'accepted':
                    self._my_clan = clan
                elif response['result'] == 'pending' or response['result'] == 'rejected':
                    self._my_clan = Clan(0, '')
                else:
                    self._my_clan = Clan(0, '')
                    self._state_valid = False
                    raise ClanRequestError('Unable to parse server response after trying to switch to clan ' + str(clan))
                return response['result']
        except Error.Error as err:
            raise ClanRequestError('Pykol error while trying to switch to clan ' + str(clan) + ': ' + str(err))

    def read_unknown_chat_message(self, text):
        if (('You have been accepted into the clan ' in text) or
            ('You have been denied in your application to the clan ' in text) or
            ('You have been kicked out of the clan ' in text) or
            (' has added you to their whitelist.' in text) or
            (' has removed you from their whitelist.' in text)):
            self._state_valid = False
            return True
        else:
            return False


if __name__ == '__main__':
    import os, sys
    scriptpath = os.path.abspath(__file__)
    basepath = os.path.realpath(os.path.join(os.path.dirname(scriptpath), '../..'))

    import readline
    import alea.config
    import alea.rng
    from kol.Session import Session

    aleabot_config = alea.config.AleabotConfig(alea.rng.RNG())
    aleabot_config.load(basepath)

    session = Session()
    session.login(aleabot_config.get('username'), aleabot_config.get('password'))
    print 'Login successful'

    reload_time = 60
    clanstate = ClanState()
    clanstate.set_session(session)

    # NOTE: Add your own test clan(s) here.
    test_clans = [
            Clan(90485, 'Bonus Adventures from Hell'),
            Clan(2047000942, 'Bonus Fights from Hell'),
    ]

    while True:
        s = raw_input('--> ')
        if s == 'r':
            print 'Reloading clan state...'
            clanstate.reload()
            print 'Reloaded.'
        elif s == 'u':
            print 'Updating clan state...'
            if clanstate.update(reload_time):
                print 'Updated.'
            else:
                print 'Already up to date.'
        elif s == 'p':
            print 'My clan: ' + repr(clanstate.my_clan())
            print 'My whitelists:'
            for clan in clanstate.my_whitelists():
                print repr(clan)
        elif s.split()[0] == 's':
            try:
                n = int(s.split()[1])
                print 'Switching to ' + repr(test_clans[n])
                result = clanstate.switch(test_clans[n])
                print 'Result: ' + result
            except ClanRequestError as err:
                print 'ClanRequestError: ' + str(err)
            except IndexError as err:
                print 'IndexError: ' + str(err)
            except ValueError as err:
                print 'ValueError: ' + str(err)
        elif s.split()[0] == 'l':
            try:
                print 'Leaving clan'
                result = clanstate.switch(Clan(0, ''))
                print 'Result: ' + result
            except ClanRequestError as err:
                print 'ClanRequestError: ' + str(err)
        elif s.split()[0] == 'u':
            try:
                userId = int(s.split()[1])
                print 'Fetching clan info for player with userId ' + str(userId)
                clan = clanstate.player_clan(userId)
                print 'Result: ' + repr(clan)
            except ClanRequestError as err:
                print 'ClanRequestError: ' + str(err)
            except ValueError as err:
                print 'ValueError: ' + str(err)


