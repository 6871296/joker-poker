from typing import List
from .cardclass import Card as card
from .cardset_class import Cardset_ftl as csftl
from .cardset_class import Cardset_type_ftl as cstftl

class Player:
    def __init__(self,cards:List[card]):
        self.cards=cards
    def printc(self):
        for idx, c in enumerate(self.cards):
            print(f"{idx}.  {c}{c.info()}", end='')
            print()  # 每张牌后换行
    
    def affordable_ftl(self, last_play: csftl) -> bool:
        """
        判断是否能要得起上一手牌
        
        Args:
            last_play: 上一手出的牌（Cardset_ftl对象），None表示第一手牌
        
        Returns:
            bool: 是否能压制（要得起返回True，要不起返回False）
        """
        # 如果 last_play 为 None，表示第一手牌，玩家可以出任意合法牌
        if last_play is None:
            return True
            
        last_type = last_play.playable()
        if last_type == cstftl.UNPLAYABLE:
            return False  # 上一手牌不合法，无法比较
        
        # 获取牌的点数（用于比较大小）- 使用与_cardset_class一致的斗地主点数
        def get_rank_ftl(c):
            """获取牌的斗地主点数数值，越大越强"""
            code = ord(str(c))
            if code == 0x1f0cf:
                return 17  # 大王（红色）
            if code == 0x1f0df:
                return 16  # 小王（黑色）
            rank = code & 0x0f
            # 斗地主点数：2最大(15)，然后是A(14)、K(13)...3(3)最小
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
                return rank
        
        # 判断是否为炸弹（4张相同点数的牌，非王）
        def is_bomb(cs):
            if len(cs.list) != 4:
                return False
            ranks = [get_rank_ftl(c) for c in cs.list]
            # 王的点数是16(小王)和17(大王)，不可能是炸弹
            return len(set(ranks)) == 1 and ranks[0] < 16
        
        # 判断是否为双王（火箭/王炸）
        def is_rocket(cs):
            ranks = sorted([get_rank_ftl(c) for c in cs.list])
            return ranks == [16, 17]  # 小王+大王
        
        last_is_bomb = is_bomb(last_play)
        last_is_rocket = is_rocket(last_play)
        
        # 获取玩家手牌中每种点数的牌
        player_ranks = {}
        for c in self.cards:
            rv = get_rank_ftl(c)
            if rv not in player_ranks:
                player_ranks[rv] = []
            player_ranks[rv].append(c)
        
        # 检查是否有王炸（最大，可以压一切）
        if 16 in player_ranks and 17 in player_ranks:
            return True
        
        # 如果上一手是王炸，除了王炸没有其他能压的
        if last_is_rocket:
            return False
        
        # 如果上一手是炸弹，需要更大的炸弹或王炸
        if last_is_bomb:
            last_bomb_rank = get_rank_ftl(last_play.list[0])
            for rank, cards in player_ranks.items():
                if len(cards) >= 4 and rank > last_bomb_rank:
                    return True
            return False
        
        # 普通牌型：需要同类型且点数更大，或者出炸弹/王炸
        # 1. 先检查能否用纯炸弹（4张）压制（四带二不算炸弹）
        for rank, cards in player_ranks.items():
            if len(cards) == 4:  # 只有纯四张才算炸弹
                return True
        
        # 2. 分析上一手牌的主牌点数（对于三带一/三等）
        def get_main_card_rank(cs, cs_type):
            """获取牌型中主要牌的点数"""
            rank_counts = {}
            for c in cs.list:
                rv = get_rank_ftl(c)
                rank_counts[rv] = rank_counts.get(rv, 0) + 1
            
            if cs_type in [cstftl.THREE_BANDS_AND_SINGLE, cstftl.THREE_BANDS_AND_DOUBLE]:
                # 找出现3次的牌
                for rv, count in rank_counts.items():
                    if count == 3:
                        return rv
            elif cs_type == cstftl.BOMB:
                # 纯炸弹找出现4次的牌
                for rv, count in rank_counts.items():
                    if count == 4:
                        return rv
            elif cs_type in [cstftl.FOUR_AND_TWO_SINGLE, cstftl.FOUR_AND_TWO_DOUBLE]:
                # 四带二找出现4次的牌（不算炸弹，仅用于同类型比较）
                for rv, count in rank_counts.items():
                    if count == 4:
                        return rv
            elif cs_type in [cstftl.DOUBLE, cstftl.DOUBLE_STRAIGHT]:
                # 对子/连对：找最小的对子点数（简化处理，取所有对子的最小值）
                pair_ranks = [rv for rv, count in rank_counts.items() if count >= 2]
                return min(pair_ranks) if pair_ranks else min(rank_counts.keys())
            else:
                # 单张/顺子：取最大点数
                return max(rank_counts.keys())
            return max(rank_counts.keys())
        
        last_main_rank = get_main_card_rank(last_play, last_type)
        last_len = len(last_play.list)
        
        if last_type == cstftl.SINGLE:
            # 单张：找更大的单张
            for rank in sorted(player_ranks.keys(), reverse=True):
                if rank > last_main_rank:
                    return True
                    
        elif last_type == cstftl.DOUBLE:
            # 对子：找更大的对子
            for rank in sorted(player_ranks.keys(), reverse=True):
                if len(player_ranks[rank]) >= 2 and rank > last_main_rank:
                    return True
                    
        elif last_type == cstftl.THREE_BANDS_AND_SINGLE:
            # 三带一：找更大的三张 + 任意一张
            for rank in sorted(player_ranks.keys(), reverse=True):
                if len(player_ranks[rank]) >= 3 and rank > last_main_rank:
                    # 需要额外的一张牌（不能是出的3张之一，但手牌中至少有4张才能出三带一）
                    if len(self.cards) >= 4:
                        return True
                        
        elif last_type == cstftl.THREE_BANDS_AND_DOUBLE:
            # 三带二：找更大的三张 + 一对
            for rank in sorted(player_ranks.keys(), reverse=True):
                if len(player_ranks[rank]) >= 3 and rank > last_main_rank:
                    # 需要额外的一对（可以是其他任意点数的对子）
                    for other_rank, other_cards in player_ranks.items():
                        if other_rank != rank and len(other_cards) >= 2:
                            return True
                            
        elif last_type == cstftl.STRAIGHT:
            # 顺子：找相同长度且更大的顺子
            if len(self.cards) >= last_len:
                sorted_ranks = sorted(player_ranks.keys())
                for i in range(len(sorted_ranks) - last_len + 1):
                    consecutive = all(sorted_ranks[i+j] == sorted_ranks[i] + j for j in range(last_len))
                    if consecutive and sorted_ranks[i] > last_main_rank - last_len + 1:
                        has_all = all(sorted_ranks[i+j] in player_ranks for j in range(last_len))
                        if has_all:
                            return True
                            
        elif last_type == cstftl.DOUBLE_STRAIGHT:
            # 连对：找相同长度且更大的连对
            if len(self.cards) >= last_len:
                unique_ranks = sorted(set(player_ranks.keys()))
                pair_count = last_len // 2
                for i in range(len(unique_ranks) - pair_count + 1):
                    consecutive_pairs = all(
                        len(player_ranks.get(unique_ranks[i+j], [])) >= 2 
                        for j in range(pair_count)
                    )
                    if consecutive_pairs and unique_ranks[i] > last_main_rank - pair_count + 1:
                        return True
        
        return False