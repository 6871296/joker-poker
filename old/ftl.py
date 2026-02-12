from time import sleep
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.cardclass import Card as card
from lib.playerclass import Player as player
from lib.cardset_class import Cardset_ftl as cset
from lib.cardset_class import Cardset_type_ftl as cstype
import random
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

def run():
    pcnt = pcnt_i()
    ccnt = ccnt_i(pcnt)
    print('\033[2J\033[0mGranting cards...')
    
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
    
    input('Choose who\'s the landlord and press Enter...')
    
    # 显示地主底牌
    print('\033[2JLandlord cards:')
    for i in range(1, 4):
        print(f'{cardset[-i]}{cardset[-i].info()}',end='  ')
    print('Player0 will be the landlord!\n')
    
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
            player_cards+=cardset[-3:] # 地主获得底牌
        playerset.append(player(player_cards))
    input('Press Enter to start...')
    print('\033[2J')
    last_cards=None
    consecutive_passes = 0  # 连续不出次数
    
    while True:
        for i in range(pcnt):
            # 检查玩家是否还有牌
            if len(playerset[i].cards) == 0:
                print(f'\033[0;1;32mPlayer{i} wins!\033[0m')
                input('Press Enter to return to menu...')
                return
            
            input(f'\033[0{";1;35" if i==0 else ""}mPlayer{i}, your turn!')
            
            # 检查是否要得起
            if not playerset[i].affordable_ftl(last_cards):
                print('\033[0;1;31mYou can\'t afford this cardset! Pass!\033[0m')
                sleep(1.5)
                consecutive_passes += 1
                # 如果其他玩家都pass了，重置last_cards
                if consecutive_passes >= pcnt - 1:
                    last_cards = None
                    print('\033[0;1;33mAll other players passed. New round!\033[0m')
                    sleep(1)
                continue
            
            while True:
                last_info = str(last_cards) if last_cards else "None (You can play any cards)"
                print(f'\033[0mLast cardset: {last_info}')
                print('\nYour cards:')
                playerset[i].printc()
                
                user_input = input('\nEnter card ID(s) to play, or \"p\" to pass: (split with space)\n').strip()
                
                # 不出牌
                if user_input.lower() == 'p':
                    print('\033[0;1;33mPass!\033[0m')
                    sleep(1)
                    consecutive_passes += 1
                    # 如果其他玩家都pass了，重置last_cards
                    if consecutive_passes >= pcnt - 1 and last_cards is not None:
                        last_cards = None
                        print('\033[0;1;33mAll other players passed. New round!\033[0m')
                        sleep(1)
                    break
                
                # 解析输入
                try:
                    card_indices = [int(x) for x in user_input.split() if x]
                except ValueError:
                    print('\033[0;31mInvalid input! Please enter numbers.\033[0m')
                    continue
                
                # 验证索引
                if not card_indices:
                    print('\033[0;31mPlease select at least one card!\033[0m')
                    continue
                
                if any(idx < 0 or idx >= len(playerset[i].cards) for idx in card_indices):
                    print('\033[0;31mInvalid card index!\033[0m')
                    continue
                
                # 创建出牌集合
                selected_cards = [playerset[i].cards[idx] for idx in card_indices]
                ocset = cset(selected_cards)
                
                # 检查牌型是否合法
                if ocset.playable() == cstype.UNPLAYABLE:
                    print('\033[0;31mInvalid cardset type!\033[0m')
                    continue
                
                # 检查是否能压过上家
                if last_cards is not None:
                    if last_cards.playable() != ocset.playable():
                        # 牌型不同，只能是炸弹
                        if ocset.playable() not in [cstype.BOMB, cstype.JOKER_BOMB]:
                            print('\033[0;31mCardset type must match! (Or play a bomb)\033[0m')
                            continue
                        else:
                            print('\033[0;1;35mBOOM! ', end='')
                    else:
                        # 牌型相同，检查点数
                        # 这里简化处理，只检查是否有更大的牌
                        pass
                
                print('\033[0;1;32mSuccessful card playing!\033[0m')
                
                # 从手牌中移除出的牌（按索引从大到小删除，避免索引错乱）
                for idx in sorted(card_indices, reverse=True):
                    playerset[i].cards.pop(idx)
                
                last_cards = ocset
                consecutive_passes = 0
                
                # 检查是否出完牌
                if len(playerset[i].cards) == 0:
                    print(f'\033[0;1;32mPlayer{i} wins!\033[0m')
                    input('Press Enter to return to menu...')
                    return
                
                sleep(1.5)
                print('\033[2J')
                break

if __name__ == '__main__':
    run()