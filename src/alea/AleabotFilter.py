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
This module implements a FilterManager filter to provide aleabot functionality.
"""


import kol.Error as Error
from kol.manager import FilterManager
from kol.manager import PatternManager
from kol.request.CursePlayerRequest import CursePlayerRequest
from kol.request.UneffectRequest import UneffectRequest
from kol.request.UserProfileRequest import UserProfileRequest
from kol.bot import BotUtils
from kol.util import Report
import re
import time
import alea.breakfast
import alea.clan
import alea.parser
import alea.rng
import alea.rolllimiter
import alea.util


class GenericAleabotError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class ChannelDisallowedError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class ClanlessPlayerError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class NeedWhitelistError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)


ITEM_ID_WANG = 625         # WANG
ITEM_ID_ARROW = 4939       # time's arrow
ITEM_ID_CANDYHEART = 2308  # yellow candy heart


# This global variable contains non-persistent bot state
aleabot = alea.util.Expando()

def init(rng, config):
    aleabot.rng = rng
    aleabot.config = config
    aleabot.rolllimiter = alea.rolllimiter.RollLimiter()
    aleabot.clanstate = alea.clan.ClanState()
    aleabot.kmail_check_timer = 0
    aleabot.home_clan_timer = -1


def doFilter(eventName, context, **kwargs):
    returnCode = FilterManager.CONTINUE
    if eventName == 'botProcessChat':
        returnCode = botProcessChat(context, **kwargs)
    elif eventName == "botProcessKmail":
        returnCode = botProcessKmail(context, **kwargs)
    elif eventName == 'botEndCycle':
        returnCode = botEndCycle(context, **kwargs)
    elif eventName == 'botPreLogin':
        returnCode = botPreLogin(context, **kwargs)
    return returnCode


def botPreLogin(context, **kwargs):
    returnCode = FilterManager.CONTINUE
    bot = kwargs['bot']

    # Make sure a MailboxManager is created
    bot.params['doWork:kmail'] = True

    return returnCode


def botEndCycle(context, **kwargs):
    returnCode = FilterManager.CONTINUE
    bot = kwargs['bot']

    # Check for new kmails?
    aleabot.kmail_check_timer += aleabot.config.get('time_to_sleep')
    if aleabot.kmail_check_timer >= aleabot.config.get('time_to_sleep_kmail'):
        Report.trace('bot', 'Enabling doWork:kmail')
        bot.params['doWork:kmail'] = True
        aleabot.kmail_check_timer = 0
    else:
        Report.trace('bot', 'Disabling doWork:kmail')
        bot.params.pop('doWork:kmail', None)

    # Update clan state in regular intervals (as configured)
    try:
        aleabot.clanstate.set_session(bot.session)
        if aleabot.clanstate.update(aleabot.config.get('clan_state_refresh_time')):
            Report.info('bot', 'Clan state update successful.')
            Report.trace('bot', 'I am in clan: ' + repr(aleabot.clanstate.my_clan()))
            Report.trace('bot', 'I have ' + str(len(aleabot.clanstate.my_whitelists())) + ' whitelists')
            # Set timer to switch back to home clan
            if aleabot.home_clan_timer < 0:
                aleabot.home_clan_timer = 0
    except alea.clan.ClanRequestError as err:
        Report.error('Unable to update clan state! Error: ' + str(err))

    # Switch to home clan after some delay
    if aleabot.home_clan_timer >= 0:
        aleabot.home_clan_timer += aleabot.config.get('time_to_sleep')
        if aleabot.home_clan_timer >= aleabot.config.get('home_clan_delay'):
            aleabot.home_clan_timer = -1

            # Breakfast now if not yet breakfasted today
            if 'breakfast' not in bot.states['rollover']:
                alea.breakfast.breakfast(bot.session)
                bot.states['rollover']['breakfast'] = True
                bot.writeState('rollover')

            # Switch to home clan now
            home_clan_id = aleabot.config.get('home_clan_id')
            if home_clan_id > 0 and aleabot.clanstate.my_clan().id() != home_clan_id:
                Report.info('bot', 'Switching back to home clan.')
                try:
                    aleabot.clanstate.switch(alea.clan.Clan(home_clan_id, ''))
                except alea.clan.ClanRequestError as err:
                    Report.error('Unable to switch clan! Error: ' + str(err))

    return returnCode


def botProcessKmail(context, **kwargs):
    returnCode = FilterManager.CONTINUE
    message = kwargs['kmail']
    bot = kwargs['bot']

    user_name = str(message['userName'])
    user_id = str(message['userId'])
    current_time = time.time()
    cmd = BotUtils.getKmailCommand(message)
    meat = message['meat']
    items = message['items']

    # Our response
    response = ''
    # Should items and meat be sent back?
    return_goodies = True
    # Should a candy heart be sent?
    send_heart = False

    # if 1 arrow was sent and the kmail is empty, interpret it as "arrow"
    if cmd == "" and len(items) == 1 and items[0]['id'] == ITEM_ID_ARROW and items[0]['quantity'] == 1 and meat == 0:
        cmd = 'arrow'

    if cmd == 'arrow':
        # Handle arrow request
        if len(items) == 1 and items[0]['id'] == ITEM_ID_ARROW and items[0]['quantity'] == 1 and meat == 0:
            # Everything is okay
            try:
                Report.info('bot', 'Firing arrow at player: ' + user_name)
                arrowreq = CursePlayerRequest(bot.session, user_id, ITEM_ID_ARROW)
                arrowreq.doRequest()
                return_goodies = False
            except Error.Error as err:
                if err.code == Error.ITEM_NOT_FOUND:
                    response = aleabot.config.get('error_arrow_no_arrows')
                elif err.code == Error.USER_NOT_FOUND:
                    response = aleabot.config.get('error_arrow_player_not_found')
                elif err.code == Error.USER_IN_HARDCORE_RONIN:
                    response = aleabot.config.get('error_arrow_ronin')
                elif err.code == Error.ALREADY_COMPLETED:
                    response = aleabot.config.get('error_arrow_already_hit')
                else:
                    response = aleabot.config.get('error_arrow_generic')

        elif len(items) == 0 and meat == 0:
            Report.warning('bot', 'Arrow request without arrow from ' + user_name)
            response = aleabot.config.get('kmailtext_arrow_notattached')

        else:
            Report.warning('bot', 'Arrow request with extra items or meat from ' + user_name)
            response = aleabot.config.get('kmailtext_arrow_extraattached')

    elif cmd == 'donate' or cmd == 'donation':
        # Handle donation
        if len(items) == 0 and meat == 0:
            # Empty donation kmail?
            Report.warning('bot', 'Empty donation received from ' + user_name)
            response = aleabot.config.get('kmailtext_donate_empty')
        else:
            Report.info('bot', 'Donation received from ' + user_name)
            response = aleabot.config.get('kmailtext_donate_thanks')
            return_goodies = False
            send_heart = True

    else:
        # Handle unknown command
        Report.warning('bot', 'Unknown kmail command: ' + cmd)
        response = aleabot.config.get('kmailtext_unknown')

    # Send our response
    if response != '' or (return_goodies and (len(items) != 0 or meat != 0)):
        Report.info('bot', 'Responding to kmail')
        response_kmail = {}
        response_kmail['userId'] = message['userId']
        response_kmail['text'] = format_reply(response + '\n\n' + aleabot.config.get('kmailtext_quote'), user_name=user_name, user_id=user_id, current_time=current_time) + '\n' + quote_kmail(message)
        if return_goodies:
            response_kmail['items'] = items
            response_kmail['meat'] = meat
        try:
            bot.sendKmail(response_kmail)
        except Error.Error as err:
            if err.code == Error.USER_IN_HARDCORE_RONIN:
                Report.error('bot', 'Tried to send items and meat back, but user is in Hardcore or Ronin!')
                response_kmail2 = {}
                response_kmail2['userId'] = message['userId']
                response_kmail2['text'] = format_reply(response + '\n\n' + aleabot.config.get('kmailtext_quote_ronin'), user_name=user_name, user_id=user_id, curent_time=current_time) + '\n' + quote_kmail(message)
                try:
                    bot.sendKmail(response_kmail2)
                except Error.Error as err2:
                    Report.error('bot', 'Unexpected error while sending response_kmail2: ' + str(err2))
            else:
                Report.error('bot', 'Unexpected error while sending response_kmail: ' + str(err))

    # Send a candy heart
    if send_heart:
        try:
            Report.info('bot', 'Sending candy heart to player: ' + user_name)
            heartreq = CursePlayerRequest(bot.session, user_id, ITEM_ID_CANDYHEART)
            heartreq.requestData['texta'] = 'THANK'
            heartreq.requestData['textb'] = 'YOU'
            heartreq.doRequest()
        except Error.Error as err:
            Report.error('bot', 'Couldn\'t send candy heart: ' + str(err))

    returnCode = FilterManager.FINISHED
    return returnCode

def quote_kmail(message):
    q = alea.util.prefix_lines(message['text'], '> ', False)
    if message['meat'] != 0:
        q += ('\n> Meat: %d' % message['meat'])
    for item in message['items']:
        q += ('\n> Item: %s (%d)' % (item['name'], item['quantity']))
    return q


def botProcessChat(context, **kwargs):
    returnCode = FilterManager.CONTINUE
    bot = kwargs['bot']
    chat = kwargs['chat']
    if chat['type'] in ['private']:
        # Initialize variables for response formatting
        user_name = str(chat['userName'])
        user_id = str(chat['userId'])
        current_time = time.time()
        exprlist = []
        exprresults = []
        channel = ''
        clan = alea.clan.Clan(0, '')
        target_name = ''
        target_id = '0'
        uneffectable = alea.util.Uneffectable('')
        msg = ''

        try:
            # Parse the abomination that our chat partner hath wrought
            request = alea.parser.aleabot_parse(chat['text'])

            if request[0] == 'rollrequest':
                # Handle a dice rolling request
                exprlist = request[1]
                channel = request[2]

                # Get the reply text that applies to this kind of roll request
                diceless = all(expr.classify_dice() == 0 for expr in exprlist)
                if channel == '':
                    # Private rolling
                    if diceless:
                        msg = aleabot.config.get('rolltext_diceless_private')
                    else:
                        msg = aleabot.config.get('rolltext_private')
                else:
                    # Public rolling
                    if diceless:
                        msg = aleabot.config.get('rolltext_diceless_public')
                    else:
                        msg = aleabot.config.get('rolltext_public')

                # Check if channel is allowed, and switch clan if needed
                if channel != '':
                    if channel in aleabot.config.get('channels').split():
                        # Allowed public channel (e.g. /games)
                        pass
                    elif channel in aleabot.config.get('clanchannels').split():
                        # Allowed clan channel (e.g. /clan, /hobopolis, ...)
                        aleabot.clanstate.set_session(bot.session)
                        clan = aleabot.clanstate.player_clan(user_id)
                        Report.info('bot', '%s asked me to roll in clan %s' % (user_name, clan.name()))
                        if clan.id() == 0:
                            Report.warning('bot', 'A player who is not in a clan asked me to roll in ' + channel)
                            raise ClanlessPlayerError('clanless player')
                        elif not aleabot.clanstate.have_whitelist(clan):
                            Report.warning('bot', 'I do not have a whitelist in clan %s' % clan.name())
                            raise NeedWhitelistError('need whitelist')
                        else:
                            Report.info('bot', 'I have a whitelist in clan %s' % clan.name())
                            aleabot.clanstate.switch(clan)
                            # Set timer to switch back to home clan
                            aleabot.home_clan_timer = 0
                    else:
                        raise ChannelDisallowedError(channel)

                # Apply time-based limits
                aleabot.rolllimiter.check(channel, user_id, clan.id(),
                        current_time, aleabot.config)

                # Evaluate dice expressions
                exprresults = alea.expr.aleabot_eval(exprlist,
                        channel != '', aleabot.rng, aleabot.config)

                # Update time-based roll limiter
                aleabot.rolllimiter.update(channel, user_id, clan.id(),
                        current_time, aleabot.config)

                # Record roll and result in roll verification list
                state = bot.states['global']
                rollverify_key = 'rollverify_' + user_id
                if rollverify_key not in state:
                    state[rollverify_key] = []
                state[rollverify_key].insert(0, (
                    current_time,
                    [str(x) for x in exprlist],
                    [str(x) for x in exprresults],
                    str(channel),
                    str(clan.name())))
                rollverify_count = aleabot.config.get('rollverify_count')
                state[rollverify_key] = state[rollverify_key][0:rollverify_count]
                bot.writeState('global')

            elif request[0] == 'rollverifyrequest':
                # Handle a roll verification request
                try:
                    target_name, target_id = resolve_target(bot,
                            user_name, user_id, request[1])

                    # Get config settings
                    rollverify_count = aleabot.config.get('rollverify_count')
                    rollverify_header = aleabot.config.get('rollverify_header')
                    rollverify_entry_private = aleabot.config.get('rollverify_entry_private')
                    rollverify_entry_public = aleabot.config.get('rollverify_entry_public')
                    rollverify_entry_clan = aleabot.config.get('rollverify_entry_clan')
                    
                    # Get saved list of rolls
                    state = bot.states['global']
                    rollverify_key = 'rollverify_' + target_id
                    rolls = state.get(rollverify_key, [])
                    rolls = rolls[0:rollverify_count]

                    # Build kmail
                    rollverify_kmail = {}
                    rollverify_kmail['userId'] = user_id
                    rollverify_kmail['text'] = format_reply(rollverify_header,
                            user_name=user_name,
                            user_id=user_id,
                            current_time=current_time,
                            target_name=target_name,
                            target_id=target_id)
                    rollverify_kmail['text'] += '\n\n'
                    for roll in rolls:
                        if roll[4] != '':  # clan != ''
                            rollverify_entry = rollverify_entry_clan
                        elif roll[3] != '':  # channel != ''
                            rollverify_entry = rollverify_entry_public
                        else:
                            rollverify_entry = rollverify_entry_private
                        rollverify_kmail['text'] += format_reply(rollverify_entry,
                                user_name=user_name,
                                user_id=user_id,
                                current_time=roll[0],
                                target_name=target_name,
                                target_id=target_id,
                                exprlist=roll[1],
                                exprresults=roll[2],
                                channel=roll[3],
                                clan=roll[4])
                        rollverify_kmail['text'] += '\n'

                    # Try to send the kmail
                    bot.sendKmail(rollverify_kmail)

                except Error.Error as err:
                    if err.code == Error.USER_NOT_FOUND:
                        msg = aleabot.config.get('error_rollverify_player_not_found')
                    else:
                        msg = aleabot.config.get('error_generic')


            elif request[0] == 'helprequest':
                # Handle a help request
                msg = aleabot.config.get('helptext')

            elif request[0] == 'hellorequest':
                # Handle a hello request
                msg = aleabot.config.get('hellotext')

            elif request[0] == 'thanksrequest':
                # Handle a thanks request
                msg = aleabot.config.get('thankstext')

            elif request[0] == 'timerequest':
                # Handle a time request
                msg = aleabot.config.get('timetext')

            elif request[0] == 'wangrequest':
                # Handle a wang request
                try:
                    target_name, target_id = resolve_target(bot,
                            user_name, user_id, request[1])

                    # Check limits
                    # Use 'rollover' bot state which is cleared each rollover
                    state = bot.states['rollover']
                    wang_sender_count_key = 'wang_sender_count_' + user_id
                    wang_sender_count = state.get(wang_sender_count_key, 0)
                    wang_target_count_key = 'wang_target_count_' + target_id
                    wang_target_count = state.get(wang_target_count_key, 0)
                    if target_id == str(bot.session.userId):
                        msg = aleabot.config.get('error_wang_self')
                    elif wang_sender_count >= aleabot.config.get('wang_sender_limit'):
                        msg = aleabot.config.get('error_wang_sender_limit')
                    elif wang_target_count >= aleabot.config.get('wang_target_limit'):
                        msg = aleabot.config.get('error_wang_target_limit')
                    elif target_id != user_id and ('dontwangme_' + target_id) in bot.states['global']:
                        msg = aleabot.config.get('error_wang_notwanted')
                    else:

                        # Limits not reached yet. Slap!
                        Report.info('bot', 'Slapping player with wang: ' + target_name)
                        wangreq = CursePlayerRequest(bot.session, target_id, ITEM_ID_WANG)
                        wangreq.doRequest()
                        if target_id == user_id:
                            msg = aleabot.config.get('wangtext_self')
                        else:
                            msg = aleabot.config.get('wangtext')

                        # Increase limit counters
                        state[wang_sender_count_key] = wang_sender_count + 1
                        state[wang_target_count_key] = wang_target_count + 1
                        bot.writeState('rollover')

                except Error.Error as err:
                    if err.code == Error.ITEM_NOT_FOUND:
                        msg = aleabot.config.get('error_wang_no_wangs')
                    elif err.code == Error.USER_NOT_FOUND:
                        msg = aleabot.config.get('error_wang_player_not_found')
                    else:
                        msg = aleabot.config.get('error_wang_generic')

            elif request[0] == 'arrowrequest':
                # Handle an arrow request
                try:
                    target_name, target_id = resolve_target(bot,
                            user_name, user_id, request[1])

                    # Check limits
                    # Use 'rollover' bot state which is cleared each rollover
                    state = bot.states['rollover']
                    arrow_sender_count_key = 'arrow_sender_count_' + user_id
                    arrow_sender_count = state.get(arrow_sender_count_key, 0)
                    if target_id == str(bot.session.userId):
                        msg = aleabot.config.get('error_arrow_self')
                    elif arrow_sender_count >= aleabot.config.get('arrow_sender_limit'):
                        msg = aleabot.config.get('error_arrow_sender_limit')
                    else:

                        # Limits not reached yet. Fire!
                        Report.info('bot', 'Firing arrow at player: ' + target_name)
                        arrowreq = CursePlayerRequest(bot.session, target_id, ITEM_ID_ARROW)
                        arrowreq.doRequest()
                        if target_id == user_id:
                            msg = aleabot.config.get('arrowtext_self')
                        else:
                            msg = aleabot.config.get('arrowtext')

                        # Increase limit counters
                        state[arrow_sender_count_key] = arrow_sender_count + 1
                        bot.writeState('rollover')

                except Error.Error as err:
                    if err.code == Error.ITEM_NOT_FOUND:
                        msg = aleabot.config.get('error_arrow_no_arrows')
                    elif err.code == Error.USER_NOT_FOUND:
                        msg = aleabot.config.get('error_arrow_player_not_found')
                    elif err.code == Error.USER_IN_HARDCORE_RONIN:
                        msg = aleabot.config.get('error_arrow_ronin')
                    elif err.code == Error.ALREADY_COMPLETED:
                        msg = aleabot.config.get('error_arrow_already_hit')
                    else:
                        msg = aleabot.config.get('error_arrow_generic')

            elif request[0] == 'uneffectrequest':
                # Handle an uneffect request
                uneffectable = request[1]
                if uneffectable.inputname() == '':
                    msg = aleabot.config.get('error_uneffect_no_effect_given')
                elif uneffectable.count() == 0:
                    msg = aleabot.config.get('error_uneffect_no_match')
                elif uneffectable.count() >= 2:
                    msg = aleabot.config.get('error_uneffect_too_many_matches')
                else:
                    # Exactly one effect matched
                    effect_id = uneffectable.effect_ids()[0]
                    print str(effect_id)
                    uneffectreq = UneffectRequest(bot.session, effect_id)
                    try:
                        uneffectreq.doRequest()
                        msg = aleabot.config.get('uneffecttext')
                    except Error.Error as err:
                        if err.code == Error.EFFECT_NOT_FOUND:
                            msg = aleabot.config.get('error_uneffect_not_cursed')
                        elif err.code == Error.ITEM_NOT_FOUND:
                            msg = aleabot.config.get('error_uneffect_no_sgeea')
                        else:
                            msg = aleabot.config.get('error_uneffect_generic')

            elif request[0] == 'dontwangmerequest':
                # Handle a dontwangme request
                key = 'dontwangme_' + user_id
                bot.states['global'][key] = True
                bot.writeState('global')
                msg = aleabot.config.get('dontwangmetext')

            elif request[0] == 'allowwangrequest':
                # Handle an allowwang request
                key = 'dontwangme_' + user_id
                bot.states['global'].pop(key, None)
                bot.writeState('global')
                msg = aleabot.config.get('allowwangtext')

        except GenericAleabotError:
            msg = aleabot.config.get('error_generic')
        except ChannelDisallowedError:
            msg = aleabot.config.get('error_channel_disallowed')
        except ClanlessPlayerError:
            msg = aleabot.config.get('error_clanless_player')
        except NeedWhitelistError:
            msg = aleabot.config.get('error_need_whitelist')
        except alea.clan.ClanRequestError:
            msg = aleabot.config.get('error_clan_request')
        except alea.rolllimiter.PrivatePerPlayerRollLimitError:
            msg = aleabot.config.get('error_private_perplayer_limit')
        except alea.rolllimiter.PublicPerPlayerRollLimitError:
            msg = aleabot.config.get('error_public_perplayer_limit')
        except alea.rolllimiter.PublicPerChannelRollLimitError:
            msg = aleabot.config.get('error_public_perchannel_limit')
        except alea.expr.ResultCountExceededError:
            msg = aleabot.config.get('error_too_many_results')
        except alea.expr.DiceCountExceededError:
            msg = aleabot.config.get('error_expression_too_many_dice')
        except alea.expr.DicelessDisallowedError:
            msg = aleabot.config.get('error_diceless')
        except alea.expr.D1DisallowedError:
            msg = aleabot.config.get('error_d1')
        except alea.expr.AleabotEvalError:
            msg = aleabot.config.get('error_expression_eval')
        except alea.parser.AleabotSyntaxError:
            msg = aleabot.config.get('error_bad_syntax')

        # If not explicitly chatting to a public channel or a private
        # conversation, make sure we /msg the user who is talking to us
        if msg != '' and msg[0] != '/':
            msg = '/msg %p ' + msg

        # Format reply message
        msg = format_reply(msg,
                user_name=user_name,
                user_id=user_id,
                current_time=current_time,
                exprlist=exprlist,
                exprresults=exprresults,
                channel=channel,
                clan=clan,
                target_name=target_name,
                target_id=target_id,
                uneffectable=uneffectable)

        # Chat!
        if msg != '':
            response = bot.sendChatMessage(msg)
            response_text = "\n".join(x['text'] for x in response)

            # Handle chat errors
            if 'You cannot access that channel' in response_text:
                Report.warning('bot', 'Received error while chatting: ' + response_text)
                msg = aleabot.config.get('error_channel_inaccessible')
                msg = '/msg ' + user_id + ' ' + msg
                bot.sendChatMessage(msg)

        returnCode = FilterManager.FINISHED

    elif chat['type'] in ['notification:kmail']:
        Report.info('bot', 'Kmail notification received.')

        # Make sure to check for new kmails next cycle
        # (see botEndCycle handler)
        aleabot.kmail_check_timer = aleabot.config.get('time_to_sleep_kmail')

    elif chat['type'] in ['unknown']:
        # Handle some chat messages of type 'unknown'
        # Such as: whitelist changes, clan acceptance / rejection
        aleabot.clanstate.set_session(bot.session)
        if aleabot.clanstate.read_unknown_chat_message(chat['text']):
            Report.info('bot', 'Clan state is no longer valid, need to reload.')

    return returnCode

def format_reply(msg, **kwargs):
    msg_final = ''
    for part in re.split(r'(%[PpXERCcUTt%])', msg):
        if part == '%P':
            msg_final += str(kwargs.get('user_name', ''))
        elif part == '%p':
            msg_final += str(kwargs.get('user_id', ''))
        elif part == '%X':
            current_time = float(kwargs.get('current_time', 0.0))
            tm = time.gmtime(current_time)
            msg_final += '%d/%d/%d %d:%02dz' % (tm.tm_mday, tm.tm_mon, tm.tm_year%100, tm.tm_hour, tm.tm_min)
        elif part == '%E':
            l = kwargs.get('exprlist', [])
            msg_final += ', '.join(str(x) for x in l)
        elif part == '%R':
            l = kwargs.get('exprresults', [])
            msg_final += ', '.join(str(x) for x in l)
        elif part == '%C':
            msg_final += str(kwargs.get('channel', ''))
        elif part == '%c':
            clan = kwargs.get('clan', None)
            if clan is not None:
                msg_final += str(clan)
        elif part == '%T':
            msg_final += str(kwargs.get('target_name', ''))
        elif part == '%t':
            msg_final += str(kwargs.get('target_id', ''))
        elif part == '%U':
            uneffectable = kwargs.get('uneffectable', None)
            if uneffectable is not None:
                msg_final += ', '.join(uneffectable.effect_names())
        elif part == '%%':
            msg_final += '%'
        else:
            msg_final += part
    return msg_final

def resolve_target(bot, user_name, user_id, target_name):
    if target_name == '' or target_name.lower() == 'me':
        return (user_name, user_id)
    else:
        return whois(bot, target_name)

def whois(bot, name):
    Report.trace('bot', 'Whois: ' + name)
    response = bot.sendChatMessage('/whois ' + name)
    responsetext = ''.join(x['text'] for x in response)
    match = re.search(r'<a[^>]*showplayer.php[^>]*><b[^>]*>([A-Za-z0-9_ ]+) \(#([0-9]+)\)</b></a>', responsetext)
    if match:
        player_name = match.group(1)
        player_id = match.group(2)
        Report.trace('bot', 'Whois resolved: Name: ' + str(player_name))
        Report.trace('bot', 'Whois resolved: ID: ' + str(player_id))
        return player_name, player_id
    elif 'Unknown Player: ' in responsetext:
        raise Error.Error("That player could not be found.", Error.USER_NOT_FOUND)
    else:
        Report.warning('bot', 'Unable to parse /whois response: ' + repr(responsetext))
        raise Error.Error("Unable to parse /whois response.", Error.REQUEST_GENERIC)

