from time import sleep
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.cardclass import Card as card
from lib.playerclass import Player as player
from lib.cardset_class import Cardset_type_cra as cstype
from lib.cardset_class import Cardset_cra as cset
import random

def get_card_rank(c):
    code = ord(str(c))
    rank = code & 0x0f
    # 捉红尖标准点数：5 6 7 8 9 10 J Q K A，不含2、3、4、王
    if rank == 0x01:
        return 14  # A
    elif rank == 0x0e:
        return 13  # K
    elif rank == 0x0d:
        return 12  # Q
    elif rank == 0x0b:
        return 11  # J
    elif rank == 0x0a:
        return 10  # 10
    elif rank >= 0x05 and rank <= 0x09:
        return rank  # 5-9
    return rank

def get_main_rank(cs, cs_type):
    """获取牌型中主牌的点数"""
    rank_counts = {}
    for c in cs.list:
        r = get_card_rank(c)
        rank_counts[r] = rank_counts.get(r, 0) + 1
    
    if cs_type in [cstype.BOMB3, cstype.BOMB4]:
        # 炸弹：找出现3/4次的牌
        for r, cnt in rank_counts.items():
            if cnt in [3,4]:
                return r
    elif cs_type in [cstype.DOUBLE, cstype.DOUBLE_STRAIGHT]:
        # 对子/连对：取最小的对子点数
        pair_ranks = [r for r, cnt in rank_counts.items() if cnt >= 2]
        return min(pair_ranks) if pair_ranks else min(rank_counts.keys())
    elif cs_type == cstype.BOMBDRA:
        # 双红A：固定返回16（最小值，但最大）
        return 16
    else:
        # 单张/顺子：取最大点数
        return max(rank_counts.keys())
    return max(rank_counts.keys())

def can_beat(ocset,last_cards):
    if last_cards is None:
        return True
    
    ocset_type=ocset.playable()
    last_type=last_cards.playable()
    if last_type==cstype.BOMBDRA:
        return False
    elif ocset_type==cstype.BOMBDRA:
        return True
    
    elif ocset_type==cstype.BOMB4:
        if last_type!=cstype.BOMB4:
            return True
        else:
            return get_main_rank(ocset,ocset_type)>get_main_rank(last_cards,last_type)
    elif ocset_type==cstype.BOMB3:
        if last_type!=cstype.BOMB4:
            if last_type!=cstype.BOMB3:
                return True
            else:
                return get_main_rank(ocset,ocset_type)>get_main_rank(last_cards,last_type)
        else:
            return False
    else:
        if ocset_type!=last_type:
            return False
        else:
            return get_main_rank(ocset,ocset_type)>get_main_rank(last_cards,last_type)

def pcnt_i():
    pcnt=int(input('Players count(Must be a muiple of 4):'))
    if pcnt%4!=0:
        print('\033[0;1;31mNot a mutiple of 4!\033[0m')
        sleep(1.5)
        print('\033[2J',end='')
        return pcnt_i()
    elif pcnt<4:
        print('\033[0;1;31mToo low!\033[0m')
        sleep(1.5)
        print('\033[2J',end='')
        return pcnt_i()
    else:
        return pcnt
def ccnt_i(pcnt):
    ccnt=int(input(f'Cardset(s) count(Must be a mutiple of {pcnt//4}):'))
    if ccnt%(pcnt//4)!=0:
        print(f'\033[0;1;31mNot a mutiple of {pcnt//4}!\033[0m')
        sleep(1.5)
        print('\033[2J',end='')
        return pcnt_i()
    elif ccnt<1:
        print('\033[0;1;31mToo low!\033[0m')
        sleep(1.5)
        print('\033[2J',end='')
        return ccnt_i()
    else:
        return pcnt

class AppIO:
    def __init__(self,pcnt=3,ccnt=1):
        self.pcnt=pcnt
        self.ccnt=ccnt
    def msg_cta(self,msg:dict):
        '''核心 -> 应用: 发送消息给应用层'''
        raise NotImplementedError("Subclasses must implement msg_cta()")
    def msg_atc(self) -> dict:
        '''应用 -> 核心: 从应用层接收消息'''
        raise NotImplementedError("Subclasses must implement msg_atc()")
def sort_cards(cards):
    return sorted(cards,key=get_card_rank,reverse=True)

def run(app:AppIO):
    pcnt=app.pcnt
    ccnt=app.ccnt
    # 创建卡牌组（52张牌 -12张234 = 40张/副）
    # 黑桃A-K, 红心A-K, 方块A-K, 梅花A-K, 大小王
    # 注意：去掉骑士牌 (🂬🂼🃌🃜) - 现代扑克不用
    card_chars = (
        '🂡🂥🂦🂧🂨🂩🂪🂫🂭🂮'    # 黑桃 A-K (10张，去掉🂬、2、3、4)
        '🂱🂵🂶🂷🂸🂹🂺🂻🂽🂾'    # 红心 A-K (10张，去掉🂼、2、3、4)
        '🃁🃅🃆🃇🃈🃉🃊🃋🃍🃎'    # 方块 A-K (10张，去掉🃌、2、3、4)
        '🃑🃕🃖🃗🃘🃙🃚🃛🃝🃞'    # 梅花 A-K (10张，去掉🃜、2、3、4)
    )
    cardset = [card(c) for c in list(ccnt * card_chars)]
    
    random.shuffle(cardset)
    
    # 计算每人发牌数（除去3张底牌）
    cards_for_players = ccnt * 40
    cpp = cards_for_players // pcnt  # cards per player
    
    