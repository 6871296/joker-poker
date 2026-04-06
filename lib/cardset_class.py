from .cardclass import Card as card
from typing import List
from enum import Enum as enum

class Cardset_type_ftl(enum):
    UNPLAYABLE=0
    SINGLE=1
    DOUBLE=2
    BOMB=3
    THREE_BANDS_AND_SINGLE=4
    THREE_BANDS_AND_DOUBLE=5
    FOUR_AND_TWO_SINGLE=6
    FOUR_AND_TWO_DOUBLE=7
    STRAIGHT=8
    DOUBLE_STRAIGHT=9
    JOKER_BOMB=10

class Cardset_ftl:
    def __init__(self,cardlist:List[card]):
        self.list=cardlist
    
    def _get_rank(self, c):
        """
        获取牌的斗地主点数数值
        斗地主规则: 大王>小王>2>A>K>Q>J>10>9>8>7>6>5>4>3
        """
        code = ord(str(c))
        if code == 0x1f0cf:
            return 17  # 大王（红色）
        if code == 0x1f0df:
            return 16  # 小王（黑色）
        
        rank = code & 0x0f  # 原始点数
        # 斗地主点数映射
        if rank == 0x02:
            return 15  # 2
        elif rank == 0x01:
            return 14  # A
        elif rank == 0x0e:
            return 13  # K
        elif rank == 0x0d:
            return 12  # Q
        elif rank == 0x0b:
            return 11  # J
        elif rank == 0x0a:
            return 10  # 10
        elif rank >= 0x03 and rank <= 0x09:
            return rank  # 3-9
        else:
            return rank  # 其他（包括骑士牌等）
    
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
            if sorted(unique_ranks) == [16, 17]:
                return Cardset_type_ftl.JOKER_BOMB
            # 对子（非王）
            if counts == [2] and 16 not in unique_ranks and 17 not in unique_ranks:
                return Cardset_type_ftl.DOUBLE
            return Cardset_type_ftl.UNPLAYABLE
            
        elif len(self.list) == 4:
            # 炸弹或三带一
            if counts == [4] and 16 not in unique_ranks and 17 not in unique_ranks:
                return Cardset_type_ftl.BOMB
            elif counts == [3, 1]:
                return Cardset_type_ftl.THREE_BANDS_AND_SINGLE
            return Cardset_type_ftl.UNPLAYABLE
            
        elif len(self.list) == 5:
            # 三带二
            if counts == [3, 2]:
                return Cardset_type_ftl.THREE_BANDS_AND_DOUBLE
            # 顺子 (5张连续，不能有2/小王/大王)
            if (len(unique_ranks) == 5 and unique_ranks[-1] - unique_ranks[0] == 4 and
                all(r <= 14 for r in unique_ranks)):  # A(14)是最大的允许值
                return Cardset_type_ftl.STRAIGHT
            return Cardset_type_ftl.UNPLAYABLE
            
        elif len(self.list) == 6:
            # 检查连对（3对）
            if all(c == 2 for c in counts) and len(counts) == 3:
                if unique_ranks[-1] - unique_ranks[0] == 2:  # 3对连续
                    if unique_ranks[-1] <= 14:
                        return Cardset_type_ftl.DOUBLE_STRAIGHT
            # 四带二单（4+1+1）
            if counts == [4, 1, 1]:
                # 检查炸弹不是王（炸弹不能是大王或小王）
                bomb_rank = None
                for rank, count in rank_counts.items():
                    if count == 4 and rank < 16:
                        bomb_rank = rank
                        break
                if bomb_rank is not None:
                    return Cardset_type_ftl.FOUR_AND_TWO_SINGLE
            return Cardset_type_ftl.UNPLAYABLE
            
        elif len(self.list) == 8:
            # 检查连对（4对）
            if all(c == 2 for c in counts) and len(counts) == 4:
                if unique_ranks[-1] - unique_ranks[0] == 3:  # 4对连续
                    if unique_ranks[-1] <= 14:
                        return Cardset_type_ftl.DOUBLE_STRAIGHT
            # 四带两对（4+2+2）
            if counts == [4, 2, 2]:
                # 检查炸弹不是王
                bomb_rank = None
                for rank, count in rank_counts.items():
                    if count == 4 and rank < 16:
                        bomb_rank = rank
                        break
                if bomb_rank is not None:
                    return Cardset_type_ftl.FOUR_AND_TWO_DOUBLE
            return Cardset_type_ftl.UNPLAYABLE
            
        else:
            # 更多牌的情况
            # 检查顺子（5张以上连续，无重复，不能有2/小王/大王）
            if len(unique_ranks) == len(self.list) and len(self.list) >= 5:
                if unique_ranks[-1] - unique_ranks[0] == len(self.list) - 1:
                    # 顺子中最大的牌不能超过A(14)
                    if unique_ranks[-1] <= 14:
                        return Cardset_type_ftl.STRAIGHT
            
            # 检查连对（3对以上连续的对子，不能有2/小王/大王）
            if all(c == 2 for c in counts) and len(counts) >= 3:
                if unique_ranks[-1] - unique_ranks[0] == len(counts) - 1:
                    # 连对中最大的牌不能超过A(14)
                    if unique_ranks[-1] <= 14:
                        return Cardset_type_ftl.DOUBLE_STRAIGHT
            
            return Cardset_type_ftl.UNPLAYABLE
    
    def __str__(self):
        s=''
        for i in self.list:
            s+=f' \033[0m{i}{i.info()}\033[0m'
        return s

class Cardset_type_cra(enum):
    UNPLAYABLE=0
    SINGLE=1
    DOUBLE=2
    STRAIGHT=3
    DOUBLE_STRAIGHT=4
    BOMB3=5
    BOMB4=6
    BOMBDRA=7

class Cardset_cra:
    def __init__(self,cardlist:List[card]):
        self.list=cardlist
    def _get_rank(self,c):
        code = ord(str(c))
        # 捉红尖标准点数：5 6 7 8 9 10 J Q K A，不含2、3、4、王
        rank = code & 0x0f  # 原始点数
        # 斗地主点数映射
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
        else:
            return rank  # 其他（包括骑士牌等）
    def playable(self):
        if len(self.list)<1:
            return Cardset_type_cra.UNPLAYABLE
        rank_counts={}
        for c in self.list:
            rank=self._get_rank(c)
            rank_counts[rank]=rank_counts.get(rank,0)+1
        counts = sorted(rank_counts.values(), reverse=True)
        unique_ranks = sorted(rank_counts.keys())
        
        if len(self.list)==1:
            return Cardset_type_cra.SINGLE
        elif len(self.list==2):
            if sorted(self.list)==[card('🂱'),card('🃁')]:
                return Cardset_type_cra.BOMBDRA
            elif counts==[2]:
                return Cardset_type_cra.DOUBLE
            return Cardset_type_cra.UNPLAYABLE
        elif len(self.list)==3:
            if self.list[0]==self.list[1]==self.list[2]:
                return Cardset_type_cra.BOMB3
            return Cardset_type_cra.UNPLAYABLE
        elif len(self.list)==4:
            if self.list[0]==self.list[1]==self.list[2]==self.list[3]:
                return Cardset_type_cra.BOMB4
            return Cardset_type_cra.UNPLAYABLE
        else:
            if len(unique_ranks) == len(self.list) and len(self.list) >= 5:
                if unique_ranks[-1] - unique_ranks[0] == len(self.list) - 1:
                    # 顺子中最大的牌不能超过A(14)
                    if unique_ranks[-1] <= 14:
                        return Cardset_type_cra.STRAIGHT
            if all(c == 2 for c in counts) and len(counts) >= 3:
                if unique_ranks[-1] - unique_ranks[0] == len(counts) - 1:
                    # 连对中最大的牌不能超过A(14)
                    if unique_ranks[-1] <= 14:
                        return Cardset_type_ftl.DOUBLE_STRAIGHT
        return Cardset_type_cra.UNPLAYABLE
    def __str__(self):
        s=''
        for i in self.list:
            s+=f' \033[0m{i}{i.info()}\033[0m'
        return s