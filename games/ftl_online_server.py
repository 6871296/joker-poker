import socket
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.getip import get_local_ip, get_public_ip
from lib.serverclass import Server
from lib.cardclass import Card as card
from lib.cardset_class import Cardset_ftl as cset
from lib.cardset_class import Cardset_type_ftl as cstype
import random
import threading

class FTLServer:
    def __init__(self, port=5555, max_players=3):
        self.server = Server(host='0.0.0.0', port=port, max_players=max_players)
        self.cardset = []
        self.players_cards = {}  # {player_id: [cards]}
        self.current_turn = 0
        self.last_cards = None
        self.consecutive_passes = 0
        self.landlord_id = 0
        self.max_players = max_players
        self.game_lock = threading.Lock()
        
    def start(self):
        """启动服务器并等待游戏开始"""
        # 在单独线程中启动服务器
        server_thread = threading.Thread(target=self.server.start)
        server_thread.daemon = True
        server_thread.start()
        
        # 等待用户开始游戏
        input('\033[0;33mPress Enter when all players are ready to start...\033[0m')
        
        with self.server.lock:
            player_count = self.server.get_player_count()
            if player_count < 2:
                print('\033[0;31mNot enough players! Need at least 2.\033[0m')
                return
            self._init_game()
    
    def _init_game(self):
        """初始化游戏"""
        # 创建卡牌组（52张牌 + 2张王牌 = 54张）
        card_chars = (
            '🂡🂢🂣🂤🂥🂦🂧🂨🂩🂪🂫🂭🂮'    # 黑桃 A-K
            '🂱🂲🂳🂴🂵🂶🂷🂸🂹🂺🂻🂽🂾'    # 红心 A-K
            '🃁🃂🃃🃄🃅🃆🃇🃈🃉🃊🃋🃍🃎'    # 方块 A-K
            '🃑🃒🃓🃔🃕🃖🃗🃘🃙🃚🃛🃝🃞'    # 梅花 A-K
            '🃏🃟'  # 大王、小王
        )
        self.cardset = [card(c) for c in list(card_chars)]
        random.shuffle(self.cardset)
        
        # 获取参与游戏的玩家
        active_players = []
        for pid, client_info in self.server.clients.items():
            if not client_info.get('is_spectator', False):
                active_players.append(pid)
        
        active_players.sort()
        self.max_players = len(active_players)
        
        # 计算每人发牌数（除去3张底牌）
        cards_for_players = 54 - 3
        cpp = cards_for_players // self.max_players
        
        # 选择地主（第一个玩家）
        self.landlord_id = active_players[0]
        
        # 发牌
        idx = 0
        for i, pid in enumerate(active_players):
            start = i * cpp
            end = start + cpp
            player_cards = self.cardset[start:end]
            if pid == self.landlord_id:
                player_cards += self.cardset[-3:]  # 地主获得底牌
            self.players_cards[pid] = player_cards
            # 通知玩家手牌
            self._send_cards_to_player(pid, player_cards)
        
        # 发送游戏开始和地主信息
        self.server._broadcast(f'game_start {self.landlord_id}')
        print(f'\033[0;32mGame started! Landlord is Player {self.landlord_id}\033[0m')
        
        # 启动游戏循环
        self._game_loop(active_players)
    
    def _send_cards_to_player(self, player_id, cards):
        """发送手牌信息给玩家"""
        if player_id not in self.server.clients:
            return
        card_strs = [str(c) for c in cards]
        msg = f'your_cards {len(cards)} ' + ' '.join(card_strs)
        self.server._send_msg(self.server.clients[player_id]['socket'], msg)
    
    def _game_loop(self, active_players):
        """游戏主循环"""
        current_idx = 0
        
        while True:
            current_player = active_players[current_idx]
            
            # 检查玩家是否还有牌
            if len(self.players_cards.get(current_player, [])) == 0:
                self.server._broadcast(f'win {current_player}')
                print(f'\033[0;1;32mPlayer {current_player} wins!\033[0m')
                input('Press Enter to end server...')
                self.server.stop()
                return
            
            # 发送轮到某玩家
            self.server.send_turn(current_player)
            print(f'\033[0;35mTurn: Player {current_player}\033[0m')
            
            # 等待玩家出牌
            if not self._wait_for_play(current_player):
                # 玩家断开连接或出错
                self.server._broadcast(f'disconnect {current_player}')
                print(f'\033[0;31mPlayer {current_player} disconnected!\033[0m')
                return
            
            # 移动到下一个玩家
            current_idx = (current_idx + 1) % len(active_players)
    
    def _wait_for_play(self, player_id):
        """等待玩家出牌"""
        client_socket = self.server.clients[player_id]['socket']
        
        while True:
            try:
                data = self.server._recv_msg(client_socket)
                if not data:
                    return False  # 连接断开
                
                parts = data.split(' ')
                cmd = parts[0]
                
                if cmd == 'play':
                    # play <玩家编号> <剩余手牌数> <牌数> <牌1> <牌2>...
                    if len(parts) < 4:
                        self.server._send_msg(client_socket, 'error Invalid play command')
                        continue
                    
                    pid = int(parts[1])
                    remaining = int(parts[2])
                    card_count = int(parts[3])
                    
                    if pid != player_id:
                        self.server._send_msg(client_socket, 'error Not your turn')
                        continue
                    
                    played_cards = []
                    if card_count > 0:
                        card_strs = parts[4:4+card_count]
                        # 根据牌面字符找到对应的Card对象
                        for cs in card_strs:
                            for c in self.players_cards[player_id]:
                                if str(c) == cs:
                                    played_cards.append(c)
                                    break
                        
                        # 验证牌型
                        ocset = cset(played_cards)
                        if ocset.playable() == cstype.UNPLAYABLE:
                            self.server._send_msg(client_socket, 'error Invalid cardset type')
                            continue
                        
                        # 验证是否能压过上家
                        if self.last_cards is not None:
                            if not self._can_beat(self.last_cards, ocset):
                                self.server._send_msg(client_socket, 'error Cannot beat last cards')
                                continue
                    
                    # 从手牌中移除
                    for c in played_cards:
                        self.players_cards[player_id].remove(c)
                    
                    # 更新状态
                    if card_count > 0:
                        self.last_cards = cset(played_cards)
                        self.consecutive_passes = 0
                    else:
                        self.consecutive_passes += 1
                    
                    # 广播出牌
                    self.server.send_play(player_id, len(self.players_cards[player_id]), played_cards)
                    print(f'\033[0;32mPlayer {player_id} played {card_count} cards\033[0m')
                    
                    # 检查是否所有人都要不起
                    if self.consecutive_passes >= self.max_players - 1:
                        self.last_cards = None
                        self.server._broadcast('new_round')
                        print('\033[0;1;33mNew round!\033[0m')
                    
                    return True
                
                elif cmd == 'chat':
                    # chat <玩家编号> <消息>
                    if len(parts) < 3:
                        continue
                    pid = int(parts[1])
                    message = ' '.join(parts[2:])[:128]  # 限制128字符
                    is_spectator = self.server.clients[pid].get('is_spectator', False)
                    self.server.broadcast_chat(pid, message, is_spectator)
                    print(f'\033[0;36mChat from {pid}: {message}\033[0m')
                
                elif cmd == 'leave':
                    # leave <玩家编号>
                    pid = int(parts[1])
                    if pid == player_id:
                        self.server.remove_player(pid)
                        return False
                
                elif cmd == 'peek':
                    # peek <玩家编号> - 转为旁观者
                    pid = int(parts[1])
                    if pid == player_id:
                        self.server.player_to_spectator(pid)
                        # 从active_players中移除，游戏继续
                        self.server._broadcast(f'player_peek {pid}')
                        print(f'\033[0;33mPlayer {pid} became spectator\033[0m')
                        return True
                
                elif cmd == 'kick':
                    # kick <玩家编号> - 仅房主可用
                    if len(parts) < 2:
                        continue
                    target_id = int(parts[1])
                    if player_id == self.landlord_id:  # 只有地主可以踢人
                        self.server.kick_player(target_id)
                
                else:
                    self.server._send_msg(client_socket, f'error Unknown command: {cmd}')
                    
            except Exception as e:
                print(f'\033[0;31mError handling player {player_id}: {e}\033[0m')
                return False
    
    def _can_beat(self, last_cards, new_cards):
        """检查新牌是否能压过上一手牌"""
        last_type = last_cards.playable()
        new_type = new_cards.playable()
        
        if new_type == cstype.JOKER_BOMB:
            return True  # 王炸最大
        
        if last_type == cstype.JOKER_BOMB:
            return False  # 不能压王炸
        
        if new_type == cstype.BOMB:
            if last_type != cstype.BOMB:
                return True  # 炸弹可以压非炸弹
            # 都是炸弹，比较大小
            return self._compare_bomb(new_cards, last_cards)
        
        if last_type != new_type:
            return False  # 牌型不同且不是炸弹
        
        # 同牌型比较大小
        return self._compare_same_type(new_cards, last_cards, new_type)
    
    def _compare_bomb(self, bomb1, bomb2):
        """比较两个炸弹大小"""
        def get_rank(c):
            code = ord(str(c))
            if code == 0x1f0cf:
                return 17
            if code == 0x1f0df:
                return 16
            return code & 0x0f
        
        rank1 = get_rank(bomb1.list[0])
        rank2 = get_rank(bomb2.list[0])
        return rank1 > rank2
    
    def _compare_same_type(self, cards1, cards2, card_type):
        """比较同类型牌的大小"""
        def get_rank(c):
            code = ord(str(c))
            if code == 0x1f0cf:
                return 17
            if code == 0x1f0df:
                return 16
            rank = code & 0x0f
            # 斗地主点数转换
            if rank == 0x02:
                return 15
            elif rank == 0x01:
                return 14
            elif rank == 0x0e:
                return 13
            elif rank == 0x0d:
                return 12
            elif rank == 0x0b:
                return 11
            elif rank == 0x0a:
                return 10
            else:
                return rank
        
        def get_main_rank(cs, cs_type):
            """获取牌型的主牌点数"""
            rank_counts = {}
            for c in cs.list:
                rv = get_rank(c)
                rank_counts[rv] = rank_counts.get(rv, 0) + 1
            
            if cs_type in [cstype.THREE_BANDS_AND_SINGLE, cstype.THREE_BANDS_AND_DOUBLE]:
                for rv, count in rank_counts.items():
                    if count == 3:
                        return rv
            elif cs_type in [cstype.DOUBLE, cstype.DOUBLE_STRAIGHT]:
                pair_ranks = [rv for rv, count in rank_counts.items() if count >= 2]
                return min(pair_ranks) if pair_ranks else min(rank_counts.keys())
            
            return max(rank_counts.keys())
        
        rank1 = get_main_rank(cards1, card_type)
        rank2 = get_main_rank(cards2, card_type)
        return rank1 > rank2


def run():
    print('\033[2J\033[0m=== JOKER POKER - Fight The Landlord Server ===')
    print()
    
    # 获取端口
    try:
        port = int(input('Enter server port (default 5555): ') or '5555')
    except ValueError:
        port = 5555
    
    # 获取玩家数量
    try:
        max_players = int(input('Enter max players (default 3): ') or '3')
        if max_players < 2:
            max_players = 2
    except ValueError:
        max_players = 3
    
    print(f'\n\033[0;32mStarting server on port {port} for {max_players} players...\033[0m')
    
    server = FTLServer(port=port, max_players=max_players)
    print('\033[0;1;32mServer started!\033[0m')
    print(f'LAN IP: \033[0;1m{get_local_ip()}')
    print(f'Public IP: \033[0;1m{get_public_ip()}\033[0m')
    print('Share this to your friends to let them join!')
    print('Press ⌃C to quickly stop the server.')
    try:
        server.start()
    except KeyboardInterrupt:
        print('\n\033[0;33mShutting down server...\033[0m')
        server.server.stop()


if __name__ == '__main__':
    run()
