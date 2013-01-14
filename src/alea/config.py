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
import re
import ConfigParser
import alea.util

#
# List of config file sections.
#
# Each tuple (section, doc) defines a section.
# - section is the name of the section
# - doc is documentation appearing in the default config file
#
sections = [

        ('auth',
            """The auth section contains KoL username and password."""),

        ('bot',
            """The bot section defines miscellaneous bot parameters."""),

        ('limits',
            """The limits section defines limits that prevent abuse of the bot."""),

        ('chatter',
            """The chatter section defines bot responses.

            Variables that may be used in responses:
                %P = player name
                %p = player ID
                %X = Xpovos = date and time (UTC)
            Roll request responses only:
                %E = expression list
                %R = result list
                %C = channel
                %c = clan
            Wang, arrow and roll verify request responses only:
                %T = target name
                %t = target ID
            Uneffect request responses only:
                %U = matching effect names

            %% becomes a single percent sign.
            """),

]

#
# List of config settings.
#
# Each tuple (section, name, type, default, doc) defines a setting.
# - section is the name of the section the setting appears in
# - name is the name of the setting
# - type is the data type; one of 'string', 'int', 'bool', 'stringchoice'
#   stringchoice means: one of the configured strings is selected at random
# - default is the default value appearing in the default config file
#   this is NOT used to supply values for missing settings;
#   a missing setting always results in an error.
# - doc is documentation appearing in the default config file
#
# Note that setting names must unique within the whole config file,
# not only the section.
#
settings = [

        # [auth]

        ('auth', 'username', 'string', None,
            """Username"""),
        ('auth', 'password', 'string', None,
            """Password"""),

        # [bot]

        ('bot', 'time_to_sleep', 'int', 5,
            """Number of seconds between chat updates"""),
        ('bot', 'time_to_sleep_kmail', 'int', 120,
            """Number of seconds between kmail updates"""),
        ('bot', 'clan_state_refresh_time', 'int', 3600,
            """Number of seconds between forced clan state updates.
            A clan state update refreshes internal variables that store the
            clan the bot is currently in, as well as the list of clans that
            have whitelisted the bot. 0 to disable forced updates."""),
        ('bot', 'home_clan_delay', 'int', 120,
            """Number of seconds to wait before switching back to home clan."""),
        ('bot', 'home_clan_id', 'int', 2046985919,
            """Clan ID of the bot's home clan"""),

        ('bot', 'rollverify_count', 'int', 20,
            """Number of entries in roll verification mail"""),

        ('bot', 'report_level', 'int', 500,
            """Console report level
            Typical values:
            300: Show errors only
            400: Show warnings and errors
            500: Show informational messages, warnings and errors
            600: Show trace messages in addition to the above
            700: Show debug messages in addition to the above"""),

        ('bot', 'log_file', 'string', 'log/aleabot',
            """Log file prefix (relative to application directory)
            Leave empty to disable all logging"""),
        ('bot', 'log_level', 'int', 500,
            """ Log level, see report_level for values"""),

        # [limits]

        ('limits', 'channels', 'string', 'games',
            """Channels where public rolling is permitted for anyone, space separated"""),
        ('limits', 'clanchannels', 'string', 'clan hobopolis slimetube hauntedhouse',
            """Channels where clan-wide rolling is permitted for anyone, space separated"""),

        ('limits', 'private_perplayer_limit', 'int', 1,
            """Number of seconds to wait between private rolls (per player)
            0 to disable"""),
        ('limits', 'private_perplayer_burst', 'int', 3,
            """Allow this many private rolls at once (per player)
            0 to disable"""),
        ('limits', 'public_perplayer_limit', 'int', 60,
            """Number of seconds to wait between public rolls for the same player
            0 to disable"""),
        ('limits', 'public_perchannel_limit', 'int', 60,
            """Number of seconds to wait between public rolls (per channel)
            0 to disable"""),

        ('limits', 'allow_diceless_public', 'bool', True,
            """Allow public diceless rolls?"""),
        ('limits', 'allow_diceless_private', 'bool', True,
            """Allow private diceless rolls?"""),
        ('limits', 'allow_d1_public', 'bool', True,
            """Allow public D1 rolls?"""),
        ('limits', 'allow_d1_private', 'bool', True,
            """Allow private D1 rolls?"""),

        ('limits', 'expression_count_max', 'int', 10,
            """Maximum permitted expression count"""),
        ('limits', 'dice_per_expression_max', 'int', 1000,
            """Allow nDx rolls up to n = this number (cumulative within expression)"""),

        ('limits', 'wang_sender_limit', 'int', 10,
            """Maximum of wangs per sender per day"""),
        ('limits', 'wang_target_limit', 'int', 3,
            """Maximum of wangs per target per day"""),
        ('limits', 'arrow_sender_limit', 'int', 1,
            """Maximum of arrows per sender per day"""),

        # [chatter]

        ('chatter', 'rolltext_private', 'stringchoice',
            ['/msg %p Rolling %E gives %R.'],
            """Text for private rolling"""),
        ('chatter', 'rolltext_public', 'stringchoice',
            ['/%C Rolling %E for %P gives %R.'],
            """Text for public rolling"""),
        ('chatter', 'rolltext_diceless_private', 'stringchoice',
            ['/msg %p Computing %E gives %R.'],
            """Text for private diceless rolling"""),
        ('chatter', 'rolltext_diceless_public', 'stringchoice',
            ['/%C Computing %E for %P gives %R.'],
            """Text for public diceless rolling"""),

        ('chatter', 'helptext', 'stringchoice',
            ['To roll in private: /msg aleabot roll 1dX. To roll in public: /msg aleabot roll 1dX in games. See my display case for more documentation than you could wish for.'],
            """Response for helprequest"""),

        ('chatter', 'hellotext', 'stringchoice',
            ['Good day, %P! Your feeble request is?'],
            """Response for hellorequest"""),

        ('chatter', 'thankstext', 'stringchoice',
            ['You\'re welcome! Anything else I can do for you?'],
            """Response for thanksrequest"""),

        ('chatter', 'timetext', 'stringchoice',
            ['It is currently %X.'],
            """Response for timerequest"""),

        ('chatter', 'wangtext', 'stringchoice',
            ['%T has been slapped with a wang.'],
            """Response for wangrequest"""),
        ('chatter', 'wangtext_self', 'stringchoice',
            ['You have been slapped with a wang.'],
            """Response for reflexive wangrequest"""),

        ('chatter', 'arrowtext', 'stringchoice',
            ['An arrow is on its way to %T.'],
            """Response for arrowrequest"""),
        ('chatter', 'arrowtext_self', 'stringchoice',
            ['An arrow is on its way to you.'],
            """Response for reflexive arrowrequest"""),

        ('chatter', 'uneffecttext', 'stringchoice',
            ['Removing effect: %U'],
            """Response for uneffectrequest"""),

        ('chatter', 'kmailtext_arrow_notattached', 'stringchoice',
            ['I tried to interpret this message as an arrow request, but there was no arrow attached. Please attach an arrow so that I can fire it at you.'],
            """Response for kmailed arrow request with no arrow attached"""),
        ('chatter', 'kmailtext_arrow_extraattached', 'stringchoice',
            ['I tried to interpret this message as an arrow request, but there were additional items or meat attached. Please only attach an arrow so that I can fire it at you.'],
            """Response for kmailed arrow request with extra goodies attached"""),
        ('chatter', 'kmailtext_donate_thanks', 'stringchoice',
            ['Hi %P, thank you very much for your donation! It is very appreciated.'],
            """Response for kmailed donate request"""),
        ('chatter', 'kmailtext_donate_empty', 'stringchoice',
            ['I tried to interpret this message as a donation, but there was nothing attached. Did you forget something? Either way, thank you for the thought!'],
            """Response for kmailed donate request with no items or meat"""),
        ('chatter', 'kmailtext_unknown', 'stringchoice',
            ['Hi %P! I\'m aleabot, a dice rolling bot. I do not know how to interpret your message. I currently understand two types of messages:\n"arrow" (with a time\'s arrow attached) to get shot with an arrow.\n"donate" (with items or meat attached) for donation\nMy main features (such as dice rolling) are accessible via chat PM. Check my display case for help.'],
            """Response for kmail with unknown command"""),
        ('chatter', 'kmailtext_quote', 'stringchoice',
            ['Here is a copy of your message:'],
            """Sent between actual response and quoted message"""),
        ('chatter', 'kmailtext_quote_ronin', 'stringchoice',
            ['You sent some items and meat which I tried to return, but you are in Hardcore or Ronin. Contact franz1 (#2272489) if you need them back.\nHere is a copy of your message:'],
            """Like kmailtext_quote, if unable to send back items/meat due to Ronin or Hardcore"""),

        ('chatter', 'rollverify_header', 'stringchoice',
            ['Roll verification mail for %T (#%t), it is currently %X'],
            """Header of roll verification mail"""),
        ('chatter', 'rollverify_entry_private', 'stringchoice',
            ['%X %E > %R'],
            """Entry of roll verification mail (private roll)"""),
        ('chatter', 'rollverify_entry_public', 'stringchoice',
            ['%X %E > %R in %C'],
            """Entry of roll verification mail (public roll)"""),
        ('chatter', 'rollverify_entry_clan', 'stringchoice',
            ['%X %E > %R in %C (%c)'],
            """Entry of roll verification mail (clan roll)"""),

        ('chatter', 'error_generic', 'stringchoice',
            ['I am Error. *BEEP* *CRASH* *ZOT* *BEEP*'],
            """Generic error message (e.g. when getting unknown errors from server requests)"""),

        ('chatter', 'error_channel_inaccessible', 'stringchoice',
            ['I do not have access to that channel.'],
            """Error message when trying to roll in an inaccessible channel"""),
        ('chatter', 'error_channel_disallowed', 'stringchoice',
            ['Public rolls are not allowed in that channel.'],
            """Error message when trying to roll in a disallowed channel"""),
        ('chatter', 'error_clanless_player', 'stringchoice',
            ['Get into a clan first, then try that again - if you dare.'],
            """Error message when player is not in a clan but tries to roll in /clan etc."""),
        ('chatter', 'error_need_whitelist', 'stringchoice',
            ['I need a whitelist to your clan for that to work.'],
            """Error message when trying to roll in a clan without whitelist"""),
        ('chatter', 'error_clan_request', 'stringchoice',
            ['Something failed while trying to switch clans. Oops!'],
            """Error message when fetching player's clan or switching clan failed"""),

        ('chatter', 'error_private_perplayer_limit', 'stringchoice',
            ['Sorry, you have to wait for one second between private rolls.'],
            """Error message for disallowed private roll due to per-player limit"""),
        ('chatter', 'error_public_perplayer_limit', 'stringchoice',
            ['Sorry, you have to wait for one minute since the last roll.'],
            """Error message for disallowed public roll due to per-player limit"""),
        ('chatter', 'error_public_perchannel_limit', 'stringchoice',
            ['Sorry, you have to wait for one minute since the last roll.'],
            """Error message for disallowed public roll due to per-channel limit"""),
        ('chatter', 'error_too_many_expressions', 'stringchoice',
            ['I can handle only ten of these dice formulas at once. How\'d you feel if I threw that much math at you?'],
            """Error message when request contains too many expressions"""),
        ('chatter', 'error_expression_too_many_dice', 'stringchoice',
            ['More than 1000 dice in one formula? Not going to fly.'],
            """Error message when expression contains too many dice"""),
        ('chatter', 'error_diceless', 'stringchoice',
            ['No dice. (Try something like "roll 1d10 in games".)'],
            """Error message for disallowed diceless roll"""),
        ('chatter', 'error_d1', 'stringchoice',
            ['Where\'s the fun in rolling a d1?'],
            """Error message for disallowed D1 roll"""),
        ('chatter', 'error_expression_eval', 'stringchoice',
            ['That did not compute, sorry.'],
            """Error message when expression can not be evaluated for some reason"""),

        ('chatter', 'error_wang_no_wangs', 'stringchoice',
            ['My bag of wangs is empty.'],
            """Error message when no wangs are left"""),
        ('chatter', 'error_wang_player_not_found', 'stringchoice',
            ['That player doesn\'t exist.'],
            """Error message when target player is unknown"""),
        ('chatter', 'error_wang_self', 'stringchoice',
            ['No, just no.'],
            """Error message when wang target is aleabot"""),
        ('chatter', 'error_wang_target_limit', 'stringchoice',
            ['Target has already been hit with enough wangs today.'],
            """Error message when wang_target_limit has been reached"""),
        ('chatter', 'error_wang_sender_limit', 'stringchoice',
            ['You have already used enough wangs today.'],
            """Error message when wang_sender_limit has been reached"""),
        ('chatter', 'error_wang_generic', 'stringchoice',
            ['Unable to use wang for unknown reason.'],
            """Error message when wang could not be used for an unknown reason"""),
        ('chatter', 'error_arrow_no_arrows', 'stringchoice',
            ['My quiver is empty.'],
            """Error message when no arrows are left"""),
        ('chatter', 'error_arrow_player_not_found', 'stringchoice',
            ['That player doesn\'t exist.'],
            """Error message when target player is unknown"""),
        ('chatter', 'error_arrow_ronin', 'stringchoice',
            ['Target is in Ronin or Hardcore.'],
            """Error message when target is in ronin or hardcore"""),
        ('chatter', 'error_arrow_already_hit', 'stringchoice',
            ['Target has already been hit with an arrow today.'],
            """Error message when target has already been hit with an arrow"""),
        ('chatter', 'error_arrow_self', 'stringchoice',
            ['I haven\'t learnt the feat of shooting straight up yet.'],
            """Error message when arrow target is aleabot"""),
        ('chatter', 'error_arrow_sender_limit', 'stringchoice',
            ['You have already used an arrow today.'],
            """Error message when arrow_sender_limit has been reached"""),
        ('chatter', 'error_arrow_generic', 'stringchoice',
            ['Unable to fire an arrow for unknown reason.'],
            """Error message when arrow could not be fired for an unknown reason"""),

        ('chatter', 'error_uneffect_no_effect_given', 'stringchoice',
            ['Please specify the effect you want me to remove.'],
            """Error message when uneffect request contained no effect name"""),
        ('chatter', 'error_uneffect_no_match', 'stringchoice',
            ['I don\'t know that effect.'],
            """Error message when uneffect request did not match a known effect"""),
        ('chatter', 'error_uneffect_too_many_matches', 'stringchoice',
            ['Too many matches found, please be more specific: %U'],
            """Error message when uneffect request matched multiple known effects"""),
        ('chatter', 'error_uneffect_not_cursed', 'stringchoice',
            ['I do not currently have that effect: %U'],
            """Error message when uneffect request contained an effect we're not cursed with"""),
        ('chatter', 'error_uneffect_no_sgeea', 'stringchoice',
            ['I do not have any soft green echo eyedrop antidotes. Would you be kind enough to send me some?'],
            """Error message when uneffect request was valid but we're out of SGEEAs"""),
        ('chatter', 'error_uneffect_generic', 'stringchoice',
            ['Unable to remove effect for unknown reason.'],
            """Error message when uneffect request failed for some unknown reason"""),

        ('chatter', 'error_rollverify_player_not_found', 'stringchoice',
            ['That player doesn\'t exist.'],
            """Error message when target player is unknown"""),

        ('chatter', 'error_bad_syntax', 'stringchoice',
            [
                'I don\'t understand. English is not my native tongue, if what you typed even was English.',
                'Huh?',
                'You don\'t make any sense to me. You never seem to make any sense to me.',
                'Come again? (That\'s what she said.)',
                'Sorry, I have no blasted idea what you could be talking about. Try /msg aleabot help?'
            ],
            """Syntax error messages"""),

]

class AleabotConfigError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class AleabotConfig(object):
    def __init__(self, rng):
        self._values = {}
        self._rng = rng

    def is_loaded(self):
        for settingsection, setting, settingtype, default, doc in settings:
            if setting not in self._values:
                return False
        return True

    def load_defaults(self):
        for settingsection, setting, settingtype, default, doc in settings:
            if default is not None:
                self._values[setting] = default

    def load(self, basepath):
        newvalues = {}
        try:
            configpath = os.path.join(basepath, 'aleabot.conf')
            config = ConfigParser.RawConfigParser()
            config.read(configpath)
            for settingsection, setting, settingtype, default, doc in settings:
                if settingtype == 'string':
                    value = config.get(settingsection, setting)
                elif settingtype == 'int':
                    value = config.getint(settingsection, setting)
                elif settingtype == 'bool':
                    value = config.getboolean(settingsection, setting)
                elif settingtype == 'stringchoice':
                    i = -1
                    value = []
                    while True:
                        if i == -1:
                            setting_i = setting
                        else:
                            setting_i = setting + '_' + str(i)
                        if config.has_option(settingsection, setting_i):
                            value.append(config.get(settingsection, setting_i))
                        elif i >= 1:
                            break
                        i += 1
                    if len(value) == 0:
                        # Raise a NoOptionError
                        config.get(settingsection, setting)
                else:
                    raise ValueError('AleabotConfig.load(): bad settingtype ' + settingtype)
                self._values[setting] = value
        except ConfigParser.Error as err:
            raise AleabotConfigError(str(err))
        except ValueError as err:
            raise AleabotConfigError(str(err))
        for setting, value in newvalues.iteritems():
            self._values[setting] = value

    def get(self, setting):
        value = self._values[setting]
        if type(value) == list:
            assert(len(value) >= 1)
            random_index = self._rng.get_one(0, len(value)-1)
            return value[random_index]
        else:
            return value

    def set(self, setting, value):
        # TODO? Validate name and type of setting
        self._values[setting] = value

    def write(self, outfile):
        outfile.write(
            '##\n' +
            '## Aleabot configuration file\n' +
            '##\n')
        for section, sectiondoc in sections:
            outfile.write(
                    '\n\n' +
                    alea.util.prefix_lines(sectiondoc, '## ', True) +
                    '[' + section + ']\n')

            for settingsection, setting, settingtype, default, doc in settings:
                if settingsection != section:
                    continue
                outfile.write('\n' + alea.util.prefix_lines(doc, '# ', False))
                value = self._values.get(setting) # returns None if not set
                if value is None or (type(value) == list and len(value) == 0):
                    outfile.write('# THIS SETTING MUST BE DEFINED\n')
                    self._writesetting('#' + setting, '', outfile)
                elif settingtype == 'bool':
                    if value:
                        self._writesetting(setting, 'yes', outfile)
                    else:
                        self._writesetting(setting, 'no', outfile)
                elif settingtype == 'stringchoice':
                    assert(type(value) == list)
                    if len(value) == 1:
                        self._writesetting(setting, value[0], outfile)
                    else:
                        for i in range(1, len(value)+1):
                            setting_i = setting + '_' + str(i)
                            self._writesetting(setting_i, value[i-1], outfile)
                else:
                    self._writesetting(setting, value, outfile)

    def _writesetting(self, setting, value, outfile):
        outfile.write(setting + ' = ' + str(value).replace('\n', '\n\t') + '\n')

    def __repr__(self):
        return 'AleabotConfig(%s)' % repr(self._values)

