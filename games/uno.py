from time import sleep
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.unocard_class import *
from lib.uno_cardset_creator import *
from lib.uno_supports import *
from core.UnoCore import run as core_run
from core.UnoCore import AppIO
from random import shuffle, choice
from simple_term_menu import TerminalMenu

COLOR_NAMES = {
    UnoColor.RED: 'Red',
    UnoColor.GREEN: 'Green',
    UnoColor.BLUE: 'Blue',
    UnoColor.YELLOW: 'Yellow',
    UnoColor.BLACK: 'Wild'
}


def card_str(c):
    """返回带 ANSI 颜色的牌字符串"""
    return f"{c.color}{c.name}\033[0m"


def choose_color():
    """让玩家选择颜色，返回索引 0-3"""
    print("\nChoose the color you want:")
    print(f"  0. {UnoColor.RED}Red\033[0m")
    print(f"  1. {UnoColor.GREEN}Green\033[0m")
    print(f"  2. {UnoColor.BLUE}Blue\033[0m")
    print(f"  3. {UnoColor.YELLOW}Yellow\033[0m")
    while True:
        user_input = input("Color index (0-3): ").strip()
        if user_input == "":
            return 0
        try:
            idx = int(user_input)
            if 0 <= idx <= 3:
                return idx
            print("Please enter 0-3.")
        except ValueError:
            print("Invalid input.")


def choose_player(options, title="Choose a player:"):
    """通过菜单选择一位玩家"""
    if len(options) == 1:
        return options[0]
    opts = [f"Player {i}" for i in options]
    menu = TerminalMenu(opts, title=title, menu_cursor=" ➤ ")
    idx = menu.show()
    return options[idx]


class LocalAppIO(AppIO):
    '''本地控制台 AppIO 实现'''

    def __init__(self, pcnt):
        super().__init__(pcnt)
        self.last_msg = None
        self._last_request = None
        self._pending_options = None

    def msg_cta(self, msg: dict):
        '''处理从核心发来的消息'''
        self.last_msg = msg
        msg_type = msg.get('type')

        if msg_type == 'turn':
            self._render_turn(msg)
        elif msg_type == 'choose_color':
            self._last_request = 'color'
        elif msg_type == 'choose_player':
            self._last_request = 'player'
            self._pending_options = msg.get('options', [])
        elif msg_type == 'play_echo':
            result = msg.get('result')
            if result == 'success':
                print('\033[0;1;32mSuccessful card playing!\033[0m')
            elif result == 'defend':
                print(f"\033[0;1;32m{msg.get('message', 'Defended!')}\033[0m")
            elif result == 'reverse_punish':
                print(f"\033[0;1;33m{msg.get('message', 'Reversed!')}\033[0m")
            elif result == 'skipped':
                print(f"\033[0;1;33m{msg.get('message', 'Skipped!')}\033[0m")
            else:
                print(f"\033[0;31m{msg.get('message', 'Error')}\033[0m")
            sleep(1.5)
        elif msg_type == 'draw_echo':
            print(f"Drew: {card_str(msg['card'])}")
            if msg.get('can_play'):
                print("This card is playable!")
            else:
                print("Cannot play this card.")
            sleep(1.5)
        elif msg_type == 'punish_draw':
            print(f"\033[0;1;31mDrawing {msg['count']} cards...\033[0m")
            sleep(1.5)
        elif msg_type == 'uno':
            print(f"\033[0;1;35mPlayer {msg['player']}: UNO!\033[0m")
            sleep(1)
        elif msg_type == 'handwash_pick':
            from_pl = msg['from_player']
            cards = msg['cards']
            print(f"\n\033[0;1;36mHANDWASH: Pick a card from Player {from_pl}'s hand\033[0m")
            for i, c in enumerate(cards):
                print(f"  {i}. {card_str(c)}")
            self._last_request = 'handwash_pick'
        elif msg_type == 'handwash_distribute':
            total = msg['total']
            pcnt = msg['pcnt']
            print(f"\n\033[0;1;36mHANDWASH: Distribute {total} cards among {pcnt} players\033[0m")
            print("Enter how many cards each player gets (space separated, e.g. '1 1 1'):")
            self._last_request = 'handwash_distribute'
            self._hw_total = total
            self._hw_pcnt = pcnt
        elif msg_type == 'handwash_echo':
            print(f"\033[0;1;33mHand wash complete! Distribution: {msg['distribution']}\033[0m")
            sleep(1.5)
        elif msg_type == 'player_win':
            print(f"\033[0;1;32mPlayer {msg['winner']} wins!\033[0m")
            input('Press Enter to return to menu...')

    def _render_turn(self, msg):
        """渲染回合状态到终端"""
        print('\033[2J')
        plid = msg['plid']
        last = msg['last']
        current_color = msg['current_color']

        print(f"\033[0;1;36m=== Player {plid}'s turn ===\033[0m")
        print(f"Last card: {card_str(last)} | Current color: {current_color}{COLOR_NAMES.get(current_color, 'Unknown')}\033[0m")
        print(f"Direction: {'→' if msg['direction'] == 1 else '←'} | Deck: {msg['deck_count']} | Discard: {msg['discard_count']}")

        if msg['draw_stack'] > 0:
            print(f"\033[0;1;31mStacked draw: +{msg['draw_stack']}\033[0m")
        if msg['pending_skip']:
            ctype = 'reverse' if msg['skip_type'] == 'reverse' else 'mute'
            print(f"\033[0;1;33mPending {ctype} challenge!\033[0m")

        # 显示各玩家手牌数
        counts = msg['player_card_counts']
        print("Hand counts: " + " | ".join([f"P{i}:{counts[i]}" for i in range(len(counts))]))
        print()

        # 显示当前玩家手牌
        cards = msg['your_cards']
        playable = msg.get('playable_indices', [])
        respond = msg.get('respond_indices', [])

        print("Your cards:")
        for i, c in enumerate(cards):
            marker = ""
            if i in respond:
                marker = " (+)"
            elif i in playable:
                marker = " ✓"
            # 完全不可出的牌，编号变灰
            if i not in playable and i not in respond:
                num = f"\033[0;90m{i}.\033[0m"
            else:
                num = f"{i}."
            print(f"  {num} {card_str(c)}{marker}")
        print()

    def msg_atc(self) -> dict:
        '''从用户获取输入并返回给核心'''
        # 处理 pending 的选择请求
        if self._last_request == 'color':
            self._last_request = None
            color_idx = choose_color()
            return {'type': 'color', 'color_idx': color_idx}

        if self._last_request == 'player':
            self._last_request = None
            target = choose_player(self._pending_options)
            self._pending_options = None
            return {'type': 'player', 'player_idx': target}

        if self._last_request == 'handwash_pick':
            self._last_request = None
            try:
                return {'type': 'handwash_pick', 'card_idx': int(input('Card index: ').strip())}
            except ValueError:
                return {'type': 'handwash_pick', 'card_idx': 0}

        if self._last_request == 'handwash_distribute':
            self._last_request = None
            user_input = input('Distribution: ').strip()
            try:
                dist = [int(x) for x in user_input.split()]
                return {'type': 'handwash_distribute', 'distribution': dist}
            except ValueError:
                return {'type': 'handwash_distribute', 'distribution': [1] * self._hw_pcnt}

        # 正常输入（根据当前回合状态决定可用操作）
        msg_type = self.last_msg.get('type') if self.last_msg else None

        if msg_type == 'turn':
            respond = self.last_msg.get('respond_indices', [])
            playable = self.last_msg.get('playable_indices', [])

            if respond:
                # 惩罚/挑战阶段：可以出响应牌或 pass
                while True:
                    user_input = input('Enter card index to respond, or "p" to pass: ').strip()
                    if user_input.lower() == 'p':
                        return {'type': 'pass'}
                    try:
                        idx = int(user_input)
                        if idx in respond:
                            return {'type': 'play', 'card_idx': idx}
                        print('\033[0;31mCannot respond with this card!\033[0m')
                    except ValueError:
                        print('\033[0;31mInvalid input!\033[0m')

            if playable:
                # 有可出牌，可以出也可以摸
                while True:
                    user_input = input('Enter card index to play, or "d" to draw: ').strip()
                    if user_input.lower() == 'd':
                        return {'type': 'draw'}
                    try:
                        idx = int(user_input)
                        if idx in playable:
                            return {'type': 'play', 'card_idx': idx}
                        print('\033[0;31mCannot play this card!\033[0m')
                    except ValueError:
                        print('\033[0;31mInvalid input!\033[0m')

            # 无可出牌，必须摸牌
            input('No playable cards. Press Enter to draw...')
            return {'type': 'draw'}

        if msg_type == 'draw_echo':
            if self.last_msg.get('can_play'):
                while True:
                    user_input = input('Play it? (y/n): ').strip().lower()
                    if user_input == 'y':
                        return {'type': 'play'}
                    elif user_input == 'n':
                        return {'type': 'pass'}
                    print('\033[0;31mPlease enter y or n!\033[0m')
            else:
                input('Press Enter to continue...')
                return {'type': 'pass'}

        # 兜底
        return {'type': 'pass'}


def pcnt_i():
    pcnt = int(input('Players count: '))
    if pcnt > 1:
        return pcnt
    else:
        print('\033[0;31mThere has to be at least 2 players!\033[0m')
        sleep(1.5)
        print('\033[2J')
        return pcnt_i()


def run():
    pcnt = pcnt_i()
    print("\033[2J\033[0mGranting cards...")

    # 创建 AppIO 实例
    io = LocalAppIO(pcnt)

    # 运行核心游戏逻辑
    core_run(io)


if __name__ == '__main__':
    run()
