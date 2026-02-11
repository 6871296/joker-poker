from .cardclass import Card as card
from typing import List
from enum import Enum as enum
from math import floor

class Cardset_type_ftl(enum):
    UNPLAYABLE=0
    SINGLE=1
    DOUBLE=2
    BOMB=3
    THREE_BANDS_AND_SINGLE=4
    THREE_BANDS_AND_DOUBLE=5
    BOMB_AND_SINGLE=6
    BOMB_AND_DOUBLE=7
    STRAIGHT=8
    DOUBLE_STRAIGHT=9
    JOKER_BOMB=10

class Cardset_ftl:
    def __init__(self,cardlist:List[card]):
        self.list=cardlist
    
    def _get_rank(self, c):
        """获取牌的点数数值"""
        code = ord(str(c))
        if code == 0x1f0cf:
            return 16  # 大王
        if code == 0x1f0df:
            return 15  # 小王
        return code & 0x0f  # 点数
    
    def playable(self):
        if len(self.list) < 1:
            return Cardset_type_ftl.UNPLAYABLE
        
        # 使用点数作为统计键
        rank_counts = {}
        for c in self.list:
            rank = self._get_rank(c)
            rank_counts[rank] = rank_counts.get(rank, 0) + 1
        
        counts = sorted(rank_counts.values(), reverse=True)
        unique_ranks = sorted(rank_counts.keys())
        
        if len(self.list) == 1:
            return Cardset_type_ftl.SINGLE
            
        elif len(self.list) == 2:
            # 王炸（大小王）
            if sorted(unique_ranks) == [15, 16]:
                return Cardset_type_ftl.JOKER_BOMB
            # 对子（非王）
            if counts == [2] and 15 not in unique_ranks and 16 not in unique_ranks:
                return Cardset_type_ftl.DOUBLE
            return Cardset_type_ftl.UNPLAYABLE
            
        elif len(self.list) == 4:
            # 炸弹或三带一
            if counts == [4] and 15 not in unique_ranks and 16 not in unique_ranks:
                return Cardset_type_ftl.BOMB
            elif counts == [3, 1]:
                return Cardset_type_ftl.THREE_BANDS_AND_SINGLE
            return Cardset_type_ftl.UNPLAYABLE
            
        elif len(self.list) == 5:
            # 三带二
            if counts == [3, 2]:
                return Cardset_type_ftl.THREE_BANDS_AND_DOUBLE
            # 顺子 (5张连续)
            if len(unique_ranks) == 5 and unique_ranks[-1] - unique_ranks[0] == 4:
                return Cardset_type_ftl.STRAIGHT
            return Cardset_type_ftl.UNPLAYABLE
            
        else:
            # 更多牌的情况
            # 检查顺子（5张以上连续，无重复）
            if len(unique_ranks) == len(self.list) and len(self.list) >= 5:
                if unique_ranks[-1] - unique_ranks[0] == len(self.list) - 1:
                    return Cardset_type_ftl.STRAIGHT
            
            # 检查连对（3对以上连续的对子）
            if all(c == 2 for c in counts) and len(counts) >= 3:
                if unique_ranks[-1] - unique_ranks[0] == len(counts) - 1:
                    return Cardset_type_ftl.DOUBLE_STRAIGHT
            
            return Cardset_type_ftl.UNPLAYABLE
    
    def __str__(self):
        s=''
        for i in self.list:
            s+=f' \033[0m{i}{i.info()}\033[0m'
        return s
