from time import sleep
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.cardclass import Card as card
from lib.playerclass import Player as player
from lib.cardset_class import Cardset_ftl as cset
from lib.cardset_class import Cardset_type_ftl as cstype
import random

'''
JOKER POKER 斗地主核心模块(FTLCore)使用说明

模块通过一个AppIO对象与应用层交互，AppIO需要提供以下接口：
- msg_cta(msg: dict): 用于向应用层发送消息，msg是一个字典，包含至少一个'type'字段表示消息类型，其他字段根据消息类型不同而不同
- msg_atc() -> dict: 用于从应用层接收消息，返回一个字典，包含至少一个'type'字段表示消息类型，其他字段根据消息类型不同而不同

游戏逻辑：

1. 游戏开始时，系统自动洗发牌，并通过msg_cta发送{
    'type':'landlord_cards_show',
    'cards': [card1, card2, card3]
}card1、card2、card3是地主底牌，类型为lib.cardclass.Card。
2. 系统通过msg_cta发送{
    'type':'start_game'
}表示游戏正式开始。
接下来，系统每回合开始前可能会返回以下内容：
- {
    'type':'player_unaffordable',
    'player':i
}表示玩家i无法出牌（没有合法的牌型能压过上家），需要选择pass。
- {
    'type':'player_win',
    'winner':i
}表示玩家i获胜，游戏结束。
- {
    'type':'player_turn',
    'player':i,
    'last_cards':last_info,
    'cards':playerset[i].cards
}表示轮到玩家i出牌，last_info是上家出的牌（如果有，否则为None），playerset[i].cards是玩家i当前的手牌列表，内容均为lib.cardclass.Card对象。
轮到玩家i出牌时，应用要通过msg_atc()返回以下内容之一：
- {
    'type':'player_pass'
}表示玩家选择pass。
- {
    'type':'player_play',
    'cardIDs':[idx1, idx2, ...]
}表示玩家选择出牌，cardIDs是一个整数列表，表示玩家手牌中被选中的牌的索引（从0开始）。系统会验证这些牌是否合法、能否压过上家，并通过msg_cta返回{
    'type':'card_play_echo',
    'message':'success'/'invalid_cardId'/'invalid_cardset'/'can\'t_beat',
    'cstype':ocset.playable(), # 仅message为'success'或'can\'t_beat'时返回，表示出牌的牌型
    'last_cstype':last_cards.playable() # 仅message为'can\'t_beat'时返回，表示上家牌型
}表示出牌结果，message字段说明结果类型，其他字段根据结果类型不同而不同。
如果玩家连续pass了足够多次（所有其他玩家都pass了），系统会通过msg_cta发送{
    'type':'new_round'
}表示新一轮开始，重置上家牌信息。
'''

def get_card_rank(c):
    """获取牌的斗地主点数，用于比较大小"""
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
    return rank

def get_main_rank(cs, cs_type):
    """获取牌型中主牌的点数"""
    rank_counts = {}
    for c in cs.list:
        r = get_card_rank(c)
        rank_counts[r] = rank_counts.get(r, 0) + 1
    
    if cs_type in [cstype.THREE_BANDS_AND_SINGLE, cstype.THREE_BANDS_AND_DOUBLE]:
        # 三带X：找出现3次的牌
        for r, cnt in rank_counts.items():
            if cnt == 3:
                return r
    elif cs_type == cstype.BOMB:
        # 炸弹：找出现4次的牌
        for r, cnt in rank_counts.items():
            if cnt == 4:
                return r
    elif cs_type in [cstype.DOUBLE, cstype.DOUBLE_STRAIGHT]:
        # 对子/连对：取最小的对子点数
        pair_ranks = [r for r, cnt in rank_counts.items() if cnt >= 2]
        return min(pair_ranks) if pair_ranks else min(rank_counts.keys())
    elif cs_type == cstype.JOKER_BOMB:
        # 王炸：固定返回16（最小值，但王炸最大）
        return 16
    else:
        # 单张/顺子：取最大点数
        return max(rank_counts.keys())
    return max(rank_counts.keys())

def can_beat(ocset, last_cards):
    """
    检查出的牌是否能压过上家
    返回 (can_beat, message)
    """
    if last_cards is None:
        return True, ""
    
    ocset_type = ocset.playable()
    last_type = last_cards.playable()
    
    # 王炸最大，可以压任何牌
    if ocset_type == cstype.JOKER_BOMB:
        return True, ""
    
    # 如果上家是王炸，只有王炸能压（上面已处理）
    if last_type == cstype.JOKER_BOMB:
        return False, "JOKER_BOMB can only be beaten by JOKER_BOMB!"
    
    # 如果出的是炸弹
    if ocset_type == cstype.BOMB:
        # 上家不是炸弹，可以压
        if last_type != cstype.BOMB:
            return True, ""
        # 上家也是炸弹，比较点数
        ocset_main = get_main_rank(ocset, ocset_type)
        last_main = get_main_rank(last_cards, last_type)
        if ocset_main > last_main:
            return True, ""
        else:
            return False, f"Your bomb({ocset_main}) is not bigger than last bomb({last_main})!"
    
    # 不是炸弹，牌型必须相同
    if ocset_type != last_type:
        return False, "Cardset type must match! (Or play a bomb)"
    
    # 牌型相同，比较点数
    ocset_main = get_main_rank(ocset, ocset_type)
    last_main = get_main_rank(last_cards, last_type)
    
    if ocset_main > last_main:
        return True, ""
    else:
        return False, f"Your card({ocset_main}) is not bigger than last card({last_main})!"

def pcnt_i():
    pcnt=int(input('Players count: '))
    if pcnt<=1:
        print('\033[0;31mToo low!\033[0m')
        sleep(1)
        print('\033[2J')
        pcnt=pcnt_i()
    return pcnt
def ccnt_i(pcnt):
    ccnt=int(input('Cardset(s) count: '))
    if ccnt<1:
        print('\033[0;31mToo low!\033[0m')
        sleep(1)
        print('\033[2J')
        ccnt=ccnt_i(pcnt)
    elif (ccnt*54-3)//pcnt<10:
        print('\033[0;31mCard/player too low!\033[0m')
        sleep(1)
        print('\033[2J')
        ccnt=ccnt_i(pcnt)
    elif (ccnt*54-3)%pcnt!=0:
        print(f'\033[0;31mCard can\'t split to each player!\033[0m')
        sleep(1)
        print('\033[2J')
        ccnt=ccnt_i(pcnt)
    return ccnt
def _pass():
    pass
class AppIO:
    '''AppIO基类 - 应用需要继承此类并重写方法'''
    def __init__(self, pcnt=3, ccnt=1):
        self.pcnt = pcnt
        self.ccnt = ccnt
    
    def msg_cta(self, msg: dict):
        '''核心 -> 应用: 发送消息给应用层'''
        raise NotImplementedError("Subclasses must implement msg_cta()")
    
    def msg_atc(self) -> dict:
        '''应用 -> 核心: 从应用层接收消息'''
        raise NotImplementedError("Subclasses must implement msg_atc()")

def sort_cards(cards):
    """按斗地主点数从大到小排序手牌"""
    return sorted(cards, key=get_card_rank, reverse=True)

def run(app:AppIO):
    pcnt = app.pcnt
    ccnt = app.ccnt
    
    # 创建卡牌组（52张牌 + 2张王牌 = 54张/副）
    # 黑桃A-K, 红心A-K, 方块A-K, 梅花A-K, 大小王
    # 注意：去掉骑士牌 (🂬🂼🃌🃜) - 现代扑克不用
    card_chars = (
        '🂡🂢🂣🂤🂥🂦🂧🂨🂩🂪🂫🂭🂮'    # 黑桃 A-K (13张，去掉🂬)
        '🂱🂲🂳🂴🂵🂶🂷🂸🂹🂺🂻🂽🂾'    # 红心 A-K (13张，去掉🂼)
        '🃁🃂🃃🃄🃅🃆🃇🃈🃉🃊🃋🃍🃎'    # 方块 A-K (13张，去掉🃌)
        '🃑🃒🃓🃔🃕🃖🃗🃘🃙🃚🃛🃝🃞'    # 梅花 A-K (13张，去掉🃜)
        '🃏🃟'  # 大王、小王 (2张)
    )
    cardset = [card(c) for c in list(ccnt * card_chars)]
    
    random.shuffle(cardset)
    
    # 显示地主底牌
    llcmsg={
        'type':'landlord_cards_show',
        'cards': [cardset[-i] for i in range(1, 4)]
    }
    app.msg_cta(llcmsg)
    
    # 计算每人发牌数（除去3张底牌）
    cards_for_players = ccnt * 54 - 3
    cpp = cards_for_players // pcnt  # cards per player
    
    # 创建玩家（地主获得底牌）
    # 找到地主位置（假设第一个玩家是地主）
    landlord_idx = 0
    
    playerset = []
    for i in range(pcnt):
        start = i * cpp
        end = start + cpp
        player_cards = cardset[start:end]
        if i == landlord_idx:
            player_cards += cardset[-3:] # 地主获得底牌
        # 整理手牌：按点数从大到小排序
        player_cards = sort_cards(player_cards)
        playerset.append(player(player_cards))
    app.msg_cta({
        'type':'start_game'
    })
    last_cards=None
    consecutive_passes = 0  # 连续不出次数
    
    while True:
        for i in range(pcnt):
            # 检查玩家是否还有牌
            if len(playerset[i].cards) == 0:
                app.msg_cta({
                    'type':'player_win',
                    'winner':i
                })
                return
            
            # 检查是否要得起
            if not playerset[i].affordable_ftl(last_cards):
                app.msg_cta({
                    'type':'player_unaffordable',
                    'player':i
                })
                sleep(1.5)
                consecutive_passes += 1
                # 如果其他玩家都pass了，重置last_cards
                if consecutive_passes >= pcnt - 1:
                    last_cards = None
                    app.msg_cta({
                        'type':'new_round',
                    })
                    sleep(1)
                continue
            
            while True:
                last_info = last_cards if last_cards else None
                app.msg_cta({
                    'type':'player_turn',
                    'player':i,
                    'last_cards':last_info,
                    'cards':playerset[i].cards
                })
                
                user_input = app.msg_atc()
                if user_input['type']=='player_pass':
                    sleep(1)
                    consecutive_passes += 1
                    # 如果其他玩家都pass了，重置last_cards
                    if consecutive_passes >= pcnt - 1 and last_cards is not None:
                        last_cards = None
                        app.msg_cta({
                            'type':'new_round',
                        })
                        sleep(1)
                    break
                
                # 解析输入
                try:
                    # 注意：不能直接用 if x，因为0会被当成False过滤
                    card_indices = [int(x) for x in user_input['cardIDs']]
                except ValueError:
                    app.msg_cta({
                        'type':'card_play_echo',
                        'message':'invalid_cardId'
                    })
                    continue
                
                # 验证索引
                if not card_indices:
                    app.msg_cta({
                        'type':'card_play_echo',
                        'message':'no_card_selected'
                    })
                    continue
                
                if any(idx < 0 or idx >= len(playerset[i].cards) for idx in card_indices):
                    app.msg_cta({
                        'type':'card_play_echo',
                        'message':'invalid_cardId'
                    })
                    continue
                
                # 创建出牌集合
                selected_cards = [playerset[i].cards[idx] for idx in card_indices]
                ocset = cset(selected_cards)
                
                # 检查牌型是否合法
                if ocset.playable() == cstype.UNPLAYABLE:
                    app.msg_cta({
                        'type':'card_play_echo',
                        'message':'invalid_cardset'
                    })
                    continue
                
                # 检查是否能压过上家
                if last_cards is not None:
                    can_beat_result, msg = can_beat(ocset, last_cards)
                    if not can_beat_result:
                        app.msg_cta({
                            'type':'card_play_echo',
                            'message':'can\'t_beat',
                            'cstype':ocset.playable(),
                            'last_cstype':last_cards.playable(),
                        })
                        continue
                
                app.msg_cta({
                    'type':'card_play_echo',
                    'message':'success',
                    'cstype':ocset.playable()
                })
                
                # 从手牌中移除出的牌（按索引从大到小删除，避免索引错乱）
                for idx in sorted(card_indices, reverse=True):
                    playerset[i].cards.pop(idx)
                
                # 出牌后重新整理手牌
                playerset[i].cards = sort_cards(playerset[i].cards)
                
                last_cards = ocset
                consecutive_passes = 0
                
                # 检查是否出完牌
                if len(playerset[i].cards) == 0:
                    app.msg_cta({
                        'type':'player_win',
                        'winner':i
                    })
                    return
                
                sleep(1.5)
                print('\033[2J')
                break

if __name__ == '__main__':
    run()