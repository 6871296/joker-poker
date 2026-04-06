from time import sleep
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.CRACore import run as core_run
from core.CRACore import AppIO, pcnt_i, ccnt_i

class LocalAppIO(AppIO):
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
    pcnt=pcnt_i
    ccnt=ccnt_i(pcnt)
    core_run(LocalAppIO(pcnt,ccnt))

if __name__=='__main__':
    run()