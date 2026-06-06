from time import sleep
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.playerclass import Player as PlayerClass
from core.CRACore import run as core_run
from core.CRACore import AppIO, pcnt_i, ccnt_i

class LocalAppIO(AppIO):
    def msg_cta(self, msg: dict):
        msg_type = msg.get('type')

        if msg_type == 'player_turn':
            last_cards = msg['last_cards']
            cards = msg['cards']

            can_afford = True
            if last_cards is not None:
                p = PlayerClass(cards)
                can_afford = p.affordable_ftl(last_cards)

            print('\nYour cards:')
            for i, c in enumerate(cards):
                if can_afford:
                    print(f"{i}.  {c}{c.info()}")
                else:
                    print(f"\033[0;90m{i}.\033[0m  {c}{c.info()}")

        elif msg_type == 'card_play_echo':
            message = msg.get('message')
            if message == 'success':
                print('\033[0;1;32mSuccessful card playing!\033[0m')
            else:
                print(f'\033[0;31m{message}\033[0m')

        elif msg_type == 'player_win':
            print(f'\033[0;1;32mPlayer {msg["winner"]} wins!\033[0m')
            input('Press Enter to return to menu...')

        elif msg_type == 'new_round':
            print('\033[0;1;33mNew round!\033[0m')
            sleep(1)

        elif msg_type == 'player_unaffordable':
            print(f'\033[0;1;31mPlayer {msg["player"]} can\'t afford! Pass!\033[0m')
            sleep(1.5)

        elif msg_type == 'start_game':
            print('\033[2J\033[0;1;36m=== Game Started! ===\033[0m\n')

    def msg_atc(self) -> dict:
        '''从用户获取输入并返回给核心'''
        user_input = input('\nEnter card ID(s) to play, or "p" to pass: (split with space)\n').strip()
        
        if user_input.lower() == 'p':
            print('\033[0;1;33mPass!\033[0m')
            sleep(1)
            return {'type': 'player_pass'}
        
        # 解析输入的牌索引
        try:
            # 注意：不能直接用 if x，因为0会被当成False过滤
            card_indices = [int(x) for x in user_input.split()]
            return {
                'type': 'player_play',
                'cardIDs': card_indices
            }
        except ValueError:
            return {
                'type': 'player_play',
                'cardIDs': []
            }

def run():
    pcnt=pcnt_i()
    ccnt=ccnt_i(pcnt)
    core_run(LocalAppIO(pcnt,ccnt))

if __name__=='__main__':
    run()