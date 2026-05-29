from time import sleep
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.unocard_class import *
from lib.uno_cardset_creator import *
from lib.uno_supports import *
from lib.settings_reader import get as _get_setting
from random import shuffle, choice
from simple_term_menu import TerminalMenu

COLOR_NAMES = {
    UnoColor.RED: 'Red',
    UnoColor.GREEN: 'Green',
    UnoColor.BLUE: 'Blue',
    UnoColor.YELLOW: 'Yellow',
    UnoColor.BLACK: 'Wild'
}


def pcnt_i():
    pcnt = int(input('Players count: '))
    if pcnt > 1:
        return pcnt
    else:
        print('\033[0;31mThere has to be at least 2 players!\033[0m')
        sleep(1.5)
        print('\033[2J')
        return pcnt_i()


def card_str(c):
    """返回带 ANSI 颜色的牌字符串"""
    return f"{c.color}{c.name}\033[0m"


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


def choose_color():
    """让玩家选择颜色"""
    menu = TerminalMenu(
        [
            f"{UnoColor.RED}Red\033[0m",
            f"{UnoColor.GREEN}Green\033[0m",
            f"{UnoColor.BLUE}Blue\033[0m",
            f"{UnoColor.YELLOW}Yellow\033[0m"
        ],
        title='Choose the color you want:',
        menu_cursor=" ➤ "
    )
    c = menu.show()
    colors = [UnoColor.RED, UnoColor.GREEN, UnoColor.BLUE, UnoColor.YELLOW]
    return colors[c]


def choose_player(pcnt, exclude_id, title="Choose a player:"):
    """通过菜单选择一位玩家（排除自己）"""
    valid_ids = [i for i in range(pcnt) if i != exclude_id]
    if len(valid_ids) == 1:
        return valid_ids[0]
    options = [f"Player {i}" for i in valid_ids]
    menu = TerminalMenu(options, title=title, menu_cursor=" ➤ ")
    idx = menu.show()
    return valid_ids[idx]


def run():
    pcnt = pcnt_i()
    print("\033[2J\033[0mGranting cards...")

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

    # 读取设置
    superposing = _get_setting('uno.superposing', {})
    reverse_enabled = superposing.get('reverse', True)
    mute_enabled = superposing.get('mute', True)

    # 处理初始功能牌效果（>2人模式才处理方向变化）
    if last.name == '⇆' and pcnt > 2:
        direction = -1
        plid = (plid + direction) % pcnt

    while True:
        player = players[plid]

        # 清屏显示当前回合
        print('\033[2J')
        print(f"\033[0;1;36m=== Player {plid}'s turn ===\033[0m")
        print(f"Last card: {card_str(last)} | Current color: {current_color}{COLOR_NAMES[current_color]}\033[0m")
        print(f"Direction: {'→' if direction == 1 else '←'} | Deck: {len(deck)} | Discard: {len(discard_pile)}")
        if draw_stack > 0:
            print(f"\033[0;1;31mStacked draw: +{draw_stack}\033[0m")
        if pending_skip:
            ctype = 'reverse' if skip_challenge_type == 'reverse' else 'mute'
            print(f"\033[0;1;33mPending {ctype} challenge!\033[0m")
        print()

        # ===== 跳过/反转挑战阶段 =====
        if pending_skip:
            can_respond = False
            valid_indices = []

            if skip_challenge_type == 'reverse' and pcnt == 2 and reverse_enabled:
                valid_indices = [i for i, c in enumerate(player) if c.name == '⇆']
                can_respond = len(valid_indices) > 0
            elif skip_challenge_type == 'mute' and mute_enabled:
                valid_indices = [i for i, c in enumerate(player) if c.name == ' ⃠']
                can_respond = len(valid_indices) > 0

            if can_respond:
                print("Your cards:")
                for i, c in enumerate(player):
                    marker = " (!)" if i in valid_indices else ""
                    print(f"  {i}. {card_str(c)}{marker}")
                print()
                type_name = 'reverse' if skip_challenge_type == 'reverse' else 'mute'
                user_input = input(f'Enter {type_name} card index to stack, or "p" to pass: ').strip()

                if user_input.lower() != 'p':
                    try:
                        idx = int(user_input)
                        if idx in valid_indices and is_playable(last, current_color, player[idx]):
                            card = player.pop(idx)
                            discard_pile.append(card)
                            last = card
                            current_color = card.color

                            # 检查 UNO / 胜利
                            if len(player) == 1:
                                print("\033[0;1;35mUNO!\033[0m")
                                sleep(1)
                            if len(player) == 0:
                                print(f"\033[0;1;32mPlayer {plid} wins!\033[0m")
                                input('Press Enter to return to menu...')
                                return

                            # 传递挑战给下家
                            plid = (plid + direction) % pcnt
                            sleep(1)
                            continue
                    except (ValueError, IndexError):
                        pass

            # 无法反击或选择不出：失去本回合
            pending_skip = False
            skip_challenge_type = None
            sleep(1)
            plid = (plid + direction) % pcnt
            continue

        # ===== 累积惩罚阶段 (+2/+4) =====
        if draw_stack > 0:
            superposing = _get_setting('uno.superposing', {})

            def can_stack(card_name):
                if last_plus_type is None:
                    return True
                key = last_plus_type.replace('+', 'P') + card_name.replace('+', 'P')
                return superposing.get(key, True)

            # +2/+4 可以叠加，DEF (✍) 可以防御
            respond_indices = [i for i, c in enumerate(player)
                               if (c.name in ['+2', '+4'] and can_stack(c.name)) or c.name == '✍']
            if respond_indices:
                print("Your cards:")
                for i, c in enumerate(player):
                    marker = " (+)" if i in respond_indices else ""
                    print(f"  {i}. {card_str(c)}{marker}")
                print()
                user_input = input(f'Enter card index to stack/defend, or "d" to draw {draw_stack}: ').strip()

                if user_input.lower() != 'd':
                    try:
                        idx = int(user_input)
                        if idx in respond_indices and is_playable(last, current_color, player[idx]):
                            card = player.pop(idx)
                            discard_pile.append(card)
                            last = card

                            if card.name == '✍':
                                # DEF：防御，取消所有累积惩罚
                                print("\033[0;1;32mDEF! Punishment cancelled!\033[0m")
                                draw_stack = 0
                                last_plus_type = None
                            elif card.name == '+2':
                                draw_stack += 2
                                last_plus_type = '+2'
                            elif card.name == '+4':
                                draw_stack += 4
                                last_plus_type = '+4'

                            if card.color == UnoColor.BLACK and card.name != '✍':
                                current_color = choose_color()
                            elif card.color != UnoColor.BLACK:
                                current_color = card.color

                            # 检查 UNO / 胜利
                            if len(player) == 1:
                                print("\033[0;1;35mUNO!\033[0m")
                                sleep(1)
                            if len(player) == 0:
                                print(f"\033[0;1;32mPlayer {plid} wins!\033[0m")
                                input('Press Enter to return to menu...')
                                return

                            plid = (plid + direction) % pcnt
                            sleep(1)
                            continue
                    except (ValueError, IndexError):
                        pass

            # 接受惩罚
            print(f"\033[0;1;31mDrawing {draw_stack} cards...\033[0m")
            ensure_deck(deck, discard_pile, draw_stack)
            for _ in range(draw_stack):
                if deck:
                    player.append(pick_card(deck))
            draw_stack = 0
            last_plus_type = None
            sleep(1.5)
            plid = (plid + direction) % pcnt
            continue

        # ===== 正常出牌阶段 =====
        print("Your cards:")
        playable_indices = []
        for i, c in enumerate(player):
            p = is_playable(last, current_color, c)
            marker = " ✓" if p else ""
            print(f"  {i}. {card_str(c)}{marker}")
            if p:
                playable_indices.append(i)

        print()
        user_input = input('Enter card index to play, or "d" to draw: ').strip()

        # ----- 选择摸牌 -----
        if user_input.lower() == 'd':
            ensure_deck(deck, discard_pile, 1)
            if not deck:
                print("\033[0;31mNo cards left to draw!\033[0m")
                sleep(1.5)
                plid = (plid + direction) % pcnt
                continue

            drawn = pick_card(deck)
            print(f"Drew: {card_str(drawn)}")
            player.append(drawn)

            if is_playable(last, current_color, drawn):
                choice = input('Play it? (y/n): ').strip().lower()
                if choice == 'y':
                    player.pop()  # 移除刚加入的牌
                    discard_pile.append(drawn)
                    last = drawn

                    # 处理效果
                    if drawn.color == UnoColor.BLACK:
                        if drawn.name == '+4':
                            draw_stack = 4
                            last_plus_type = '+4'
                        current_color = choose_color()
                    else:
                        current_color = drawn.color
                        if drawn.name == '⇆':
                            if pcnt == 2 and reverse_enabled:
                                pending_skip = True
                                skip_challenge_type = 'reverse'
                            elif pcnt > 2:
                                direction *= -1
                                if reverse_enabled:
                                    pending_skip = True
                                    skip_challenge_type = 'reverse'
                        elif drawn.name == ' ⃠' and mute_enabled:
                            pending_skip = True
                            skip_challenge_type = 'mute'
                        elif drawn.name == '+2':
                            draw_stack = 2
                            last_plus_type = '+2'

                    if len(player) == 0:
                        print(f"\033[0;1;32mPlayer {plid} wins!\033[0m")
                        input('Press Enter to return to menu...')
                        return

                    plid = (plid + direction) % pcnt
                    sleep(1)
                    continue
            # 不出或不可出：保留在手牌中，结束回合
            sleep(1)
            plid = (plid + direction) % pcnt
            continue

        # ----- 选择出牌 -----
        try:
            idx = int(user_input)
        except ValueError:
            print("\033[0;31mInvalid input!\033[0m")
            sleep(1)
            continue

        if idx < 0 or idx >= len(player):
            print("\033[0;31mInvalid card index!\033[0m")
            sleep(1)
            continue

        if idx not in playable_indices:
            print("\033[0;31mCannot play this card!\033[0m")
            sleep(1.5)
            continue

        card = player.pop(idx)
        discard_pile.append(card)
        last = card

        # 处理牌效果
        if card.color == UnoColor.BLACK:
            if card.name == '+4':
                draw_stack = 4
                last_plus_type = '+4'
            elif card.name == '🙌':
                # HANDWASH：先选颜色，再交换手牌
                current_color = choose_color()
                target = choose_player(pcnt, plid, "Choose a player to swap hands with:")
                print(f"\033[0;1;33mSwapping hands with Player {target}...\033[0m")
                players[plid], players[target] = players[target], players[plid]
                sleep(1.5)
                # 交换后检查目标玩家是否 UNO
                if len(players[target]) == 1:
                    print(f"\033[0;1;35mPlayer {target}: UNO!\033[0m")
                    sleep(1)
            else:
                # DEF (✍) 或其他黑色牌：仅选颜色
                current_color = choose_color()
        else:
            current_color = card.color
            if card.name == '⇆':
                if pcnt == 2 and reverse_enabled:
                    pending_skip = True
                    skip_challenge_type = 'reverse'
                elif pcnt > 2:
                    direction *= -1
                    if reverse_enabled:
                        pending_skip = True
                        skip_challenge_type = 'reverse'
            elif card.name == ' ⃠' and mute_enabled:
                pending_skip = True
                skip_challenge_type = 'mute'
            elif card.name == '+2':
                draw_stack = 2
                last_plus_type = '+2'

        # 检查 UNO / 胜利
        if len(player) == 1:
            print("\033[0;1;35mUNO!\033[0m")
            sleep(1)
        if len(player) == 0:
            print(f"\033[0;1;32mPlayer {plid} wins!\033[0m")
            input('Press Enter to return to menu...')
            return

        sleep(1)
        plid = (plid + direction) % pcnt


if __name__ == '__main__':
    run()
