import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.getip import get_local_ip, get_public_ip
from lib.serverclass import Server
from lib.cardclass import Card as card
from lib.cardset_class import Cardset_ftl as cset
from lib.cardset_class import Cardset_type_ftl as cstype
from core.FTLCore import run as core_run
from core.FTLCore import AppIO,can_beat
import random
import threading

'''
在线斗地主服务器 - 使用FTLCore核心
通过AppIO接口与核心交互，同时处理网络通信
'''

class NetworkAppIO(AppIO):
    '''网络版AppIO实现 - 桥接FTLCore和网络客户端'''
    
    def __init__(self, server: Server, max_players=3):
        super().__init__(max_players, 1)  # pcnt, ccnt
        self.server = server
        self.players_cards = {}  # {player_id: [cards]}
        self.landlord_id = 0
        self.current_turn = 0
        self.last_cards = None
        self.consecutive_passes = 0
        self.active_players = []
        self.game_lock = threading.Lock()
        self.waiting_for_input = threading.Event()
        self.input_buffer = None
        
    def msg_cta(self, msg: dict):
        '''从核心接收消息，发送到客户端'''
        msg_type = msg.get('type')
        
        if msg_type == 'landlord_cards_show':
            # 发送地主底牌给所有客户端
            cards = msg['cards']
            card_strs = [str(c) for c in cards]
            self.server._broadcast(f'landlord_cards {" ".join(card_strs)}')
            # 发送地主信息
            self.server._broadcast(f'game_start {self.landlord_id}')
            print(f'\033[0;32mGame started! Landlord is Player {self.landlord_id}\033[0m')
            
        elif msg_type == 'start_game':
            # 游戏开始信号，发送手牌给每个玩家
            for pid in self.active_players:
                self._send_cards_to_player(pid, self.players_cards[pid])
                
        elif msg_type == 'player_unaffordable':
            player = msg['player']
            print(f'\033[0;31mPlayer {player} can\'t afford, pass\033[0m')
            
        elif msg_type == 'new_round':
            self.last_cards = None
            self.server._broadcast('new_round')
            print('\033[0;1;33mNew round!\033[0m')
            
        elif msg_type == 'player_win':
            winner = msg['winner']
            self.server._broadcast(f'win {winner}')
            print(f'\033[0;1;32mPlayer {winner} wins!\033[0m')
            
        elif msg_type == 'player_turn':
            player = msg['player']
            last_cards = msg['last_cards']
            cards = msg['cards']
            
            # 更新当前玩家手牌缓存
            self.players_cards[player] = cards
            
            # 发送轮到某玩家
            self.server.send_turn(player)
            print(f'\033[0;35mTurn: Player {player}\033[0m')
            
            # 等待该玩家出牌
            self.current_turn = player
            self.waiting_for_input.clear()
            self.input_buffer = None
            
            # 启动一个线程来接收该玩家的输入
            receive_thread = threading.Thread(
                target=self._receive_player_input,
                args=(player,)
            )
            receive_thread.daemon = True
            receive_thread.start()
            
        elif msg_type == 'card_play_echo':
            message = msg.get('message')
            player = self.current_turn
            
            if message == 'success':
                cstype_val = msg.get('cstype')
                # 广播出牌信息
                if self.last_cards:
                    played_cards = list(self.last_cards.list)
                    card_strs = [str(c) for c in played_cards]
                    remaining = len(self.players_cards.get(player, []))
                    self.server.send_play(player, remaining, played_cards)
                    print(f'\033[0;32mPlayer {player} played {len(played_cards)} cards\033[0m')
                    
            elif message == 'can\'t_beat':
                # 发送错误给玩家
                if player in self.server.clients:
                    self.server._send_msg(
                        self.server.clients[player]['socket'],
                        'error Cannot beat last cards'
                    )
                    
            elif message == 'invalid_cardId':
                if player in self.server.clients:
                    self.server._send_msg(
                        self.server.clients[player]['socket'],
                        'error Invalid card index'
                    )
                    
            elif message == 'no_card_selected':
                if player in self.server.clients:
                    self.server._send_msg(
                        self.server.clients[player]['socket'],
                        'error Please select at least one card'
                    )
                    
            elif message == 'invalid_cardset':
                if player in self.server.clients:
                    self.server._send_msg(
                        self.server.clients[player]['socket'],
                        'error Invalid cardset type'
                    )
    
    def _send_cards_to_player(self, player_id, cards):
        """发送手牌信息给玩家"""
        if player_id not in self.server.clients:
            return
        card_strs = [str(c) for c in cards]
        msg = f'your_cards {len(cards)} ' + ' '.join(card_strs)
        self.server._send_msg(self.server.clients[player_id]['socket'], msg)
    
    def _receive_player_input(self, player_id):
        """在后台线程中接收玩家输入"""
        while True:
            try:
                data = self.server._recv_msg(self.server.clients[player_id]['socket'])
                if not data:
                    # 连接断开
                    self.input_buffer = {'type': 'player_pass'}  # 默认pass
                    self.waiting_for_input.set()
                    return
                
                parts = data.split(' ')
                cmd = parts[0]
                
                if cmd == 'play':
                    # play <玩家编号> <剩余手牌数> <牌数> <牌1> <牌2>...
                    if len(parts) < 4:
                        continue
                    
                    pid = int(parts[1])
                    card_count = int(parts[3])
                    
                    if pid != player_id:
                        self.server._send_msg(
                            self.server.clients[pid]['socket'],
                            'error Not your turn'
                        )
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
                            self.server._send_msg(
                                self.server.clients[player_id]['socket'],
                                'error Invalid cardset type'
                            )
                            continue
                        
                        # 使用FTLCore的can_beat验证
                        if self.last_cards is not None:
                            can_beat_result, _ = can_beat(ocset, self.last_cards)
                            if not can_beat_result:
                                self.server._send_msg(
                                    self.server.clients[player_id]['socket'],
                                    'error Cannot beat last cards'
                                )
                                continue
                        
                        # 更新最后出的牌
                        self.last_cards = ocset
                        
                        # 从手牌中移除
                        for c in played_cards:
                            self.players_cards[player_id].remove(c)
                        
                        self.consecutive_passes = 0
                    else:
                        # Pass
                        self.consecutive_passes += 1
                    
                    # 将输入放入缓冲区并通知核心
                    self.input_buffer = {
                        'type': 'player_play',
                        'cardIDs': list(range(len(played_cards)))  # 简化处理
                    }
                    self.waiting_for_input.set()
                    return
                
                elif cmd == 'chat':
                    # 聊天消息直接转发
                    if len(parts) < 3:
                        continue
                    pid = int(parts[1])
                    message = ' '.join(parts[2:])[:128]
                    is_spectator = self.server.clients[pid].get('is_spectator', False)
                    self.server.broadcast_chat(pid, message, is_spectator)
                    print(f'\033[0;36mChat from {pid}: {message}\033[0m')
                
                elif cmd == 'leave':
                    pid = int(parts[1])
                    if pid == player_id:
                        self.server.remove_player(pid)
                        self.input_buffer = {'type': 'player_pass'}
                        self.waiting_for_input.set()
                        return
                
                elif cmd == 'peek':
                    pid = int(parts[1])
                    if pid == player_id:
                        self.server.player_to_spectator(pid)
                        self.server._broadcast(f'player_peek {pid}')
                        print(f'\033[0;33mPlayer {pid} became spectator\033[0m')
                
                elif cmd == 'kick':
                    if len(parts) < 2:
                        continue
                    target_id = int(parts[1])
                    if player_id == self.landlord_id:
                        self.server.kick_player(target_id)
                
            except Exception as e:
                print(f'\033[0;31mError handling player {player_id}: {e}\033[0m')
                self.input_buffer = {'type': 'player_pass'}
                self.waiting_for_input.set()
                return
    
    def msg_atc(self) -> dict:
        '''等待玩家输入并返回给核心'''
        # 等待输入缓冲区被填充
        self.waiting_for_input.wait()
        self.waiting_for_input.clear()
        
        if self.input_buffer is None:
            return {'type': 'player_pass'}
        
        return self.input_buffer
    
    def init_game(self):
        """初始化游戏数据"""
        # 获取活跃玩家
        self.active_players = []
        for pid, client_info in self.server.clients.items():
            if not client_info.get('is_spectator', False):
                self.active_players.append(pid)
        
        self.active_players.sort()
        self.pcnt = len(self.active_players)
        
        # 选择地主
        self.landlord_id = self.active_players[0] if self.active_players else 0
        
        # 创建卡牌组
        card_chars = (
            '🂡🂢🂣🂤🂥🂦🂧🂨🂩🂪🂫🂭🂮'
            '🂱🂲🂳🂴🂵🂶🂷🂸🂹🂺🂻🂽🂾'
            '🃁🃂🃃🃄🃅🃆🃇🃈🃉🃊🃋🃍🃎'
            '🃑🃒🃓🃔🃕🃖🃗🃘🃙🃚🃛🃝🃞'
            '🃏🃟'
        )
        cardset = [card(c) for c in list(card_chars)]
        random.shuffle(cardset)
        
        # 发牌
        cards_for_players = 54 - 3
        cpp = cards_for_players // self.pcnt
        
        for i, pid in enumerate(self.active_players):
            start = i * cpp
            end = start + cpp
            player_cards = cardset[start:end]
            if pid == self.landlord_id:
                player_cards += cardset[-3:]
            self.players_cards[pid] = player_cards


class FTLServer:
    """斗地主服务器 - 包装类"""
    
    def __init__(self, port=5555, max_players=3):
        self.server = Server(host='0.0.0.0', port=port, max_players=max_players)
        self.io = None
        self.max_players = max_players
        
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
        
        # 创建AppIO并初始化游戏
        self.io = NetworkAppIO(self.server, self.max_players)
        self.io.init_game()
        
        # 运行核心游戏逻辑
        core_run(self.io)
        
        # 游戏结束
        input('Press Enter to end server...')
        self.server.stop()


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
    print(f'LAN IP: \033[0;1m{get_local_ip()}\033[0m')
    print(f'Public IP: \033[0;1m{get_public_ip()}\033[0m')
    print('Share this to your friends to let them join!')
    print('Run FTL Online Client on this computer will automatcally join this room.')
    print('Press ⌃C to quickly stop the server.')
    try:
        print('\033[0;1;32mServer started!\033[0m')
        server.start()
    except KeyboardInterrupt:
        print('\n\033[0;33mShutting down server...\033[0m')
        server.server.stop()


if __name__ == '__main__':
    run()
