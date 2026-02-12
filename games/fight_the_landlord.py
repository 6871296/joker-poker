from time import sleep
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.cardset_class import Cardset_type_ftl as cstype
from core.FTLCore import run as core_run
from core.FTLCore import AppIO, pcnt_i, ccnt_i

'''
本地斗地主 - 使用FTLCore核心
'''

class LocalAppIO(AppIO):
    '''本地控制台AppIO实现'''
    
    def __init__(self, pcnt, ccnt):
        super().__init__(pcnt, ccnt)
        self.landlord_idx = 0
        
    def msg_cta(self, msg: dict):
        '''处理从核心发来的消息'''
        msg_type = msg.get('type')
        
        if msg_type == 'landlord_cards_show':
            # 显示地主底牌
            print('\033[2JLandlord cards:')
            for c in msg['cards']:
                print(f'{c}{c.info()}', end='  ')
            print(f'\nPlayer{self.landlord_idx} will be the landlord!\n')
            input('Press Enter to start...')
            
        elif msg_type == 'start_game':
            print('\033[2J\033[0;1;36m=== Game Started! ===\033[0m\n')
            
        elif msg_type == 'player_unaffordable':
            player = msg['player']
            print(f'\033[0;1;31mPlayer{player} can\'t afford this cardset! Pass!\033[0m')
            sleep(1.5)
            
        elif msg_type == 'new_round':
            print('\033[0;1;33mAll other players passed. New round!\033[0m')
            sleep(1)
            
        elif msg_type == 'player_win':
            winner = msg['winner']
            print(f'\033[0;1;32mPlayer{winner} wins!\033[0m')
            input('Press Enter to return to menu...')
            
        elif msg_type == 'player_turn':
            player = msg['player']
            last_cards = msg['last_cards']
            cards = msg['cards']
            
            # 显示轮到谁
            color = "\033[0;1;35m" if player == 0 else "\033[0m"
            input(f'{color}Player{player}, your turn!\033[0m')
            
            # 显示上家出的牌
            if last_cards:
                print(f'\033[0mLast cardset: {last_cards}')
            else:
                print('\033[0mLast cardset: None (You can play any cards)')
            
            # 显示手牌
            print('\nYour cards:')
            for i, c in enumerate(cards):
                print(f"{i}.  {c}{c.info()}")
                
        elif msg_type == 'card_play_echo':
            message = msg.get('message')
            if message == 'success':
                cstype_val = msg.get('cstype')
                # 如果是炸弹，显示BOOM
                if cstype_val in [cstype.BOMB, cstype.JOKER_BOMB]:
                    print('\033[0;1;35mBOOM! ', end='')
                print('\033[0;1;32mSuccessful card playing!\033[0m')
                sleep(1.5)
                print('\033[2J')
            elif message == 'can\'t_beat':
                print('\033[0;31mYour cards can\'t beat the last cardset!\033[0m')
            elif message == 'invalid_cardId':
                print('\033[0;31mInvalid card index!\033[0m')
            elif message == 'no_card_selected':
                print('\033[0;31mPlease select at least one card!\033[0m')
            elif message == 'invalid_cardset':
                print('\033[0;31mInvalid cardset type!\033[0m')
            else:
                print(f'\033[0;31mError: {message}\033[0m')
    
    def msg_atc(self) -> dict:
        '''从用户获取输入并返回给核心'''
        user_input = input('\nEnter card ID(s) to play, or "p" to pass: (split with space)\n').strip()
        
        if user_input.lower() == 'p':
            print('\033[0;1;33mPass!\033[0m')
            sleep(1)
            return {'type': 'player_pass'}
        
        # 解析输入的牌索引
        try:
            card_indices = [int(x) for x in user_input.split() if x]
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
    pcnt = pcnt_i()
    ccnt = ccnt_i(pcnt)
    print('\033[2J\033[0mGranting cards...')
    
    # 创建AppIO实例
    io = LocalAppIO(pcnt, ccnt)
    
    # 运行核心游戏逻辑
    core_run(io)

if __name__ == '__main__':
    run()
