import time
import alea.util

class RollLimitError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class PrivatePerPlayerRollLimitError(RollLimitError):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class PublicPerPlayerRollLimitError(RollLimitError):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class PublicPerChannelRollLimitError(RollLimitError):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class RollLimiter(object):
    def __init__(self):
        self._public_perchannel = {}
        self._public_perplayer = {}
        self._private_perplayer = {}
        self._private_perplayer_burst = {}
        self._clockskew = False
    def check(self, channel, userId, clanId, aleabot_config):
        # clanId must be 0 if channel is not a clan channel
        t = time.time()
        if channel == '':
            # Private roll
            private_perplayer_limit = aleabot_config.get('private_perplayer_limit')
            if not self._check(self._private_perplayer, userId, private_perplayer_limit, t):
                burst = self._private_perplayer_burst.get(userId, 0)
                if burst >= aleabot_config.get('private_perplayer_burst') - 1:
                    raise PrivatePerPlayerRollLimitError('Private per-player roll limit')
        else:
            # Public roll
            public_perplayer_limit = aleabot_config.get('public_perplayer_limit')
            if not self._check(self._public_perplayer, userId, public_perplayer_limit, t):
                raise PublicPerPlayerRollLimitError('Public per-player roll limit')
            public_perchannel_limit = aleabot_config.get('public_perchannel_limit')
            if clanId not in self._public_perchannel:
                self._public_perchannel[clanId] = {}
            if not self._check(self._public_perchannel[clanId], channel, public_perchannel_limit, t):
                raise PublicPerChannelRollLimitError('Public global roll limit')
    def _check(self, container, index, limit, t):
        if index not in container:
            return True
        if container[index] > t:
            self._clockskew = True
            container[index] = t
        return container[index] + limit <= t
    def clock_skew_check(self):
        result = self._clockskew
        self._clockskew = False
        return result
    def update(self, channel, userId, clanId, aleabot_config):
        # clanId must be 0 if channel is not a clan channel
        t = time.time()
        if channel == '':
            # Private roll
            oldt = self._private_perplayer.get(userId, None)
            self._private_perplayer[userId] = t
            # (Handle bursts)
            private_perplayer_limit = aleabot_config.get('private_perplayer_limit')
            if oldt is None or oldt + private_perplayer_limit <= t:
                self._private_perplayer_burst[userId] = 0
            else:
                oldburst = self._private_perplayer_burst.get(userId, 0)
                self._private_perplayer_burst[userId] = oldburst + 1
        else:
            # Public roll
            if clanId not in self._public_perchannel:
                self._public_perchannel[clanId] = {}
            self._public_perchannel[clanId][channel] = t
            self._public_perplayer[userId] = t


if __name__ == '__main__':
    import readline
    import alea.config
    import alea.rng
    aleabot_config = alea.config.AleabotConfig(alea.rng.RNG())
    aleabot_config.load_defaults()
    aleabot_config.set('private_perplayer_limit', 10)
    aleabot_config.set('private_perplayer_burst', 5)
    aleabot_config.set('public_perplayer_limit', 600)
    aleabot_config.set('public_perchannel_limit', 60)
    limiter = RollLimiter()
    while True:
        s = raw_input('--> ')
        fields = s.split()
        try:
            if len(fields) == 0:
                pass
            elif len(fields) == 1:
                userId = int(fields[0])
                print 'Private roll for player ' + str(userId)
                limiter.check('', userId, 0, aleabot_config)
                limiter.update('', userId, 0, aleabot_config)
            elif len(fields) == 2:
                channel = fields[0]
                userId = int(fields[1])
                print 'Public roll in channel ' + channel + ' for player ' + str(userId)
                limiter.check(channel, userId, 0, aleabot_config)
                limiter.update(channel, userId, 0, aleabot_config)
            else:
                channel = fields[0]
                userId = int(fields[1])
                clanId = int(fields[2])
                print 'Clan roll in channel ' + channel + ' for player ' + str(userId) + ' in clan ' + str(clanId)
                limiter.check(channel, userId, clanId, aleabot_config)
                limiter.update(channel, userId, clanId, aleabot_config)
        except ValueError as err:
            print('Unable to parse request, make sure to only use player/clan IDs instead of names')
        except RollLimitError as err:
            print('Roll failed: ' + str(err))
