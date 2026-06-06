from time import sleep
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.unocard_class import *
from lib.uno_cardset_creator import *
from lib.uno_supports import *
from lib.settings_reader import get as _get_setting
from random import shuffle, choice


class AppIO:
    """AppIO 基类 - 应用需要继承此类并重写方法"""
    def __init__(self, pcnt=2):
        self.pcnt = pcnt

    def msg_cta(self, msg: dict):
        '''核心 -> 应用: 发送消息给应用层'''
        raise NotImplementedError("Subclasses must implement msg_cta()")

    def msg_atc(self) -> dict:
        '''应用 -> 核心: 从应用层接收消息'''
        raise NotImplementedError("Subclasses must implement msg_atc()")


def is_playable(last_card, current_color, hand_card):
    """判断 hand_card 是否可以接在 last_card 后"""
    if hand_card.color == UnoColor.BLACK:
        return True
    if hand_card.color == current_color:
        return True
    if hand_card.name == last_card.name:
        return True
    return False


def reshuffle_deck(deck, discard_pile):
    """将弃牌堆（保留最后一张）洗回牌堆"""
    if len(discard_pile) <= 1:
        return
    last = discard_pile[-1]
    new_deck = discard_pile[:-1]
    shuffle(new_deck)
    deck.extend(new_deck)
    discard_pile.clear()
    discard_pile.append(last)


def ensure_deck(deck, discard_pile, n=1):
    """确保牌堆至少有 n 张牌"""
    while len(deck) < n:
        old_len = len(deck)
        reshuffle_deck(deck, discard_pile)
        if len(deck) == old_len:
            break


def can_stack(card_name, last_plus_type, superposing):
    """判断某张 +2/+4 是否可以叠加到当前惩罚链上"""
    if last_plus_type is None:
        return True
    key = last_plus_type.replace('+', 'P') + card_name.replace('+', 'P')
    return superposing.get(key, True)


def _send_turn(app, state, plid, playable_indices=None, respond_indices=None):
    """发送回合状态给应用层"""
    msg = {
        'type': 'turn',
        'plid': plid,
        'last': state['last'],
        'current_color': state['current_color'],
        'direction': state['direction'],
        'your_cards': state['players'][plid],
        'deck_count': len(state['deck']),
        'discard_count': len(state['discard_pile']),
        'draw_stack': state['draw_stack'],
        'pending_skip': state['pending_skip'],
        'skip_type': state['skip_challenge_type'],
        'player_card_counts': [len(p) for p in state['players']],
        'reverse_punishment': state['reverse_punishment'],
        'playable_indices': playable_indices if playable_indices is not None else [],
        'respond_indices': respond_indices if respond_indices is not None else [],
    }
    app.msg_cta(msg)


def _handle_black_card(card, app, state, colors, plid):
    """处理黑色牌的效果（选颜色）"""
    app.msg_cta({'type': 'choose_color'})
    color_action = app.msg_atc()
    color_idx = color_action.get('color_idx', 0)
    state['current_color'] = colors[color_idx]


def _handle_card_effect(card, plid, state, app, colors):
    """处理出牌后的效果"""
    pcnt = state['pcnt']

    if card.name == '+4':
        state['draw_stack'] = 4
        state['last_plus_type'] = '+4'
    elif card.name == '+2':
        state['draw_stack'] = 2
        state['last_plus_type'] = '+2'
    elif card.name == '⇆':
        if pcnt == 2:
            # 双人模式：反转 = 跳过（总是生效，reverse_enabled 只控制是否可以叠加）
            state['pending_skip'] = True
            state['skip_challenge_type'] = 'reverse'
        else:
            # 多人模式：反转方向（reverse_enabled 控制是否可以叠加）
            state['direction'] *= -1
            if state['reverse_enabled']:
                state['pending_skip'] = True
                state['skip_challenge_type'] = 'reverse'
    elif card.name == ' ⃠':
        # 跳过总是生效（mute_enabled 只控制是否可以叠加）
        state['pending_skip'] = True
        state['skip_challenge_type'] = 'mute'
    elif card.name == '🙌':
        # HANDWASH：从每位玩家（含自己）手中抽一张牌，洗牌后重新分配
        drawn_cards = []
        for i in range(pcnt):
            if len(state['players'][i]) == 0:
                continue
            app.msg_cta({
                'type': 'handwash_pick',
                'from_player': i,
                'cards': state['players'][i],
            })
            pick_action = app.msg_atc()
            idx = pick_action.get('card_idx', 0)
            idx = max(0, min(idx, len(state['players'][i]) - 1))
            drawn_cards.append(state['players'][i].pop(idx))

        shuffle(drawn_cards)

        app.msg_cta({
            'type': 'handwash_distribute',
            'total': len(drawn_cards),
            'pcnt': pcnt,
        })
        dist_action = app.msg_atc()
        distribution = dist_action.get('distribution', [1] * pcnt)

        # 验证分配
        if sum(distribution) != len(drawn_cards) or any(d < 0 for d in distribution):
            base = len(drawn_cards) // pcnt
            remainder = len(drawn_cards) % pcnt
            distribution = [base] * pcnt
            for i in range(remainder):
                distribution[i] += 1

        # 发牌
        card_idx = 0
        for i in range(pcnt):
            for _ in range(distribution[i]):
                if card_idx < len(drawn_cards):
                    state['players'][i].append(drawn_cards[card_idx])
                    card_idx += 1

        app.msg_cta({'type': 'handwash_echo', 'distribution': distribution})
    # CUSTOM (✍) 和其他黑色牌：仅选颜色，无额外效果

    if card.color == UnoColor.BLACK:
        _handle_black_card(card, app, state, colors, plid)
    else:
        state['current_color'] = card.color


def _check_uno_win(app, state, plid):
    """检查 UNO 和胜利条件，返回是否已结束"""
    if len(state['players'][plid]) == 1:
        app.msg_cta({'type': 'uno', 'player': plid})
    if len(state['players'][plid]) == 0:
        app.msg_cta({'type': 'player_win', 'winner': plid})
        return True
    return False


def run(app: AppIO):
    pcnt = app.pcnt

    deck = NewUnoCardset()
    shuffle(deck)

    players = [[] for _ in range(pcnt)]
    for i in range(pcnt):
        for _ in range(7):
            players[i].append(pick_card(deck))

    discard_pile = []
    last = pick_card(deck)
    discard_pile.append(last)
    current_color = last.color

    # 如果初始牌是黑色，随机选一个颜色
    if last.color == UnoColor.BLACK:
        current_color = choice([UnoColor.RED, UnoColor.GREEN, UnoColor.BLUE, UnoColor.YELLOW])

    direction = 1
    plid = 0
    draw_stack = 0
    last_plus_type = None
    pending_skip = False
    skip_challenge_type = None

    superposing = _get_setting('uno.superposing', {})
    reverse_enabled = superposing.get('reverse', True)
    mute_enabled = superposing.get('mute', True)
    reverse_punishment = _get_setting('uno.reversePunishment', False)

    colors = [UnoColor.RED, UnoColor.GREEN, UnoColor.BLUE, UnoColor.YELLOW]

    state = {
        'pcnt': pcnt,
        'players': players,
        'deck': deck,
        'discard_pile': discard_pile,
        'last': last,
        'current_color': current_color,
        'direction': direction,
        'draw_stack': draw_stack,
        'last_plus_type': last_plus_type,
        'pending_skip': pending_skip,
        'skip_challenge_type': skip_challenge_type,
        'reverse_enabled': reverse_enabled,
        'mute_enabled': mute_enabled,
        'reverse_punishment': reverse_punishment,
    }

    # 处理初始功能牌效果（>2人模式才改变方向）
    if last.name == '⇆' and pcnt > 2:
        state['direction'] = -1
        plid = (plid + state['direction']) % pcnt

    while True:
        # 检查当前玩家是否已获胜
        if len(state['players'][plid]) == 0:
            app.msg_cta({'type': 'player_win', 'winner': plid})
            return

        # ===== 跳过/反转挑战阶段 =====
        if state['pending_skip']:
            valid_indices = []
            can_respond = False

            if state['skip_challenge_type'] == 'reverse' and pcnt == 2 and state['reverse_enabled']:
                valid_indices = [i for i, c in enumerate(state['players'][plid]) if c.name == '⇆']
                can_respond = len(valid_indices) > 0
            elif state['skip_challenge_type'] == 'mute' and state['mute_enabled']:
                valid_indices = [i for i, c in enumerate(state['players'][plid]) if c.name == ' ⃠']
                can_respond = len(valid_indices) > 0

            if can_respond:
                _send_turn(app, state, plid, respond_indices=valid_indices)
                action = app.msg_atc()

                if action['type'] == 'play':
                    idx = action.get('card_idx', -1)
                    if idx in valid_indices and is_playable(state['last'], state['current_color'], state['players'][plid][idx]):
                        card = state['players'][plid].pop(idx)
                        state['discard_pile'].append(card)
                        state['last'] = card
                        state['current_color'] = card.color

                        if _check_uno_win(app, state, plid):
                            return

                        plid = (plid + state['direction']) % pcnt
                        continue

            # 无法反击或选择不出：失去本回合
            app.msg_cta({'type': 'play_echo', 'result': 'skipped', 'message': f'Player {plid} was skipped!'})
            state['pending_skip'] = False
            state['skip_challenge_type'] = None
            plid = (plid + state['direction']) % pcnt
            continue

        # ===== 累积惩罚阶段 (+2/+4) =====
        if state['draw_stack'] > 0:
            respond_indices = [i for i, c in enumerate(state['players'][plid])
                               if (c.name in ['+2', '+4'] and can_stack(c.name, state['last_plus_type'], superposing))
                               or c.name == '✍']
            if state['reverse_punishment']:
                respond_indices.extend([i for i, c in enumerate(state['players'][plid]) if c.name == '⇆'])

            # 去重并保持顺序
            seen = set()
            respond_indices = [x for x in respond_indices if not (x in seen or seen.add(x))]

            _send_turn(app, state, plid, respond_indices=respond_indices)
            action = app.msg_atc()

            if action['type'] == 'play':
                idx = action.get('card_idx', -1)
                if idx in respond_indices and is_playable(state['last'], state['current_color'], state['players'][plid][idx]):
                    card = state['players'][plid].pop(idx)
                    state['discard_pile'].append(card)
                    state['last'] = card

                    if card.name == '✍':
                        # CUSTOM：防御，取消所有累积惩罚
                        state['draw_stack'] = 0
                        state['last_plus_type'] = None
                        app.msg_cta({'type': 'play_echo', 'result': 'defend', 'message': 'CUSTOM! Punishment cancelled!'})
                    elif card.name == '+2':
                        state['draw_stack'] += 2
                        state['last_plus_type'] = '+2'
                        app.msg_cta({'type': 'play_echo', 'result': 'success'})
                    elif card.name == '+4':
                        state['draw_stack'] += 4
                        state['last_plus_type'] = '+4'
                        app.msg_cta({'type': 'play_echo', 'result': 'success'})
                    elif card.name == '⇆' and state['reverse_punishment']:
                        # 反转惩罚：方向反转，让上家承受
                        state['direction'] *= -1
                        app.msg_cta({'type': 'play_echo', 'result': 'reverse_punish', 'message': 'Punishment reversed!'})

                    if card.color == UnoColor.BLACK and card.name != '✍':
                        _handle_black_card(card, app, state, colors, plid)
                    elif card.color != UnoColor.BLACK:
                        state['current_color'] = card.color

                    if _check_uno_win(app, state, plid):
                        return

                    plid = (plid + state['direction']) % pcnt
                    continue

            # 接受惩罚
            app.msg_cta({'type': 'punish_draw', 'count': state['draw_stack']})
            ensure_deck(state['deck'], state['discard_pile'], state['draw_stack'])
            for _ in range(state['draw_stack']):
                if state['deck']:
                    state['players'][plid].append(pick_card(state['deck']))
            state['draw_stack'] = 0
            state['last_plus_type'] = None
            plid = (plid + state['direction']) % pcnt
            continue

        # ===== 正常出牌阶段 =====
        playable_indices = [i for i, c in enumerate(state['players'][plid])
                            if is_playable(state['last'], state['current_color'], c)]

        _send_turn(app, state, plid, playable_indices=playable_indices)
        action = app.msg_atc()

        if action['type'] == 'draw':
            ensure_deck(state['deck'], state['discard_pile'], 1)
            if state['deck']:
                drawn = pick_card(state['deck'])
                can_play = is_playable(state['last'], state['current_color'], drawn)
                app.msg_cta({'type': 'draw_echo', 'card': drawn, 'can_play': can_play})
                state['players'][plid].append(drawn)

                if can_play:
                    action2 = app.msg_atc()
                    if action2['type'] == 'play':
                        # 立即打出摸到的牌
                        state['players'][plid].pop()
                        state['discard_pile'].append(drawn)
                        state['last'] = drawn

                        _handle_card_effect(drawn, plid, state, app, colors)

                        # HANDWASH 后检查所有玩家是否有人获胜
                        if drawn.name == '🙌':
                            for i in range(pcnt):
                                if len(state['players'][i]) == 0:
                                    app.msg_cta({'type': 'player_win', 'winner': i})
                                    return

                        app.msg_cta({'type': 'play_echo', 'result': 'success'})

                        if _check_uno_win(app, state, plid):
                            return

            plid = (plid + state['direction']) % pcnt
            continue

        elif action['type'] == 'play':
            idx = action.get('card_idx', -1)
            if idx not in playable_indices:
                app.msg_cta({'type': 'play_echo', 'result': 'invalid', 'message': 'Cannot play this card'})
                continue

            card = state['players'][plid].pop(idx)
            state['discard_pile'].append(card)
            state['last'] = card

            _handle_card_effect(card, plid, state, app, colors)

            # HANDWASH 后检查所有玩家是否有人获胜
            if card.name == '🙌':
                for i in range(pcnt):
                    if len(state['players'][i]) == 0:
                        app.msg_cta({'type': 'player_win', 'winner': i})
                        return

            app.msg_cta({'type': 'play_echo', 'result': 'success'})

            if _check_uno_win(app, state, plid):
                return

            plid = (plid + state['direction']) % pcnt
            continue

        elif action['type'] == 'pass':
            plid = (plid + state['direction']) % pcnt
            continue

        else:
            app.msg_cta({'type': 'play_echo', 'result': 'invalid', 'message': 'Unknown action'})
