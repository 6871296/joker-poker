import socket
import threading
from .getip import *

'''
JOKER POKER Socket传输标准：
数据传输量以"字段"为单位，一字段8字节。
字段中的空内容用\1填充。
例如，发送"Hello":
Hello\1\1\1

玩家名长度限制为4字段，即32字节(字符）。

下面内容省略填充符，字段之间用空格分隔：

1. 客户端连接后发送 "join <玩家名>" ，加入游戏。
2. 客户端连接后发送 "peek <玩家名>"，旁观游戏。（可以看到游戏状态但不能参与）
服务器返回"pending <你的玩家编号>"，等待服务器管理员接受或拒绝。
旁观游戏会自动允许，玩家加入需要服务器管理员手动接受。
服务器管理员能看到玩家的IP地址和玩家名。
如果接受，服务器返回"accept <玩家编号>"，玩家加入游戏。
如果拒绝，服务器返回"reject <玩家编号>"，玩家连接被关闭。

3. 服务器在满员后返回"start"，游戏开始。
流程：
服务器发送"turn <玩家编号>"，轮到玩家出牌。
玩家出牌后发送"play <玩家编号> <打完后剩余手牌数> <牌数（为0视为要不起或跳过）> <牌1> <牌2>..."
游戏中发送"chat <玩家编号> <消息（最长128字符）>"，玩家聊天。玩家和房主都不能看到旁观者发送的消息。
房主可以踢出旁观者，发送"kick <玩家编号>"，被踢出玩家连接被关闭。但玩家不能被踢出。
旁观者与玩家都可以自愿退出，发送"leave <玩家编号>"，连接被关闭。
玩家可以转为旁观者，发送"peek <玩家编号>"，玩家认输并变为旁观者，不能再参与游戏。
'''

def __server_joining__(client_socket, addr,username):
    response = input(f'\033[0;32mA new player joined your room!\033[0m\n{username}\n{addr[0]}:{addr[1]}\nAccept or reject? (y/n)')
    return response.lower() == 'y'

class Server:
    def __init__(self, host='0.0.0.0', port=5555, max_players=3, auto_accept=False):
        self.host = host
        self.port = port
        self.max_players = max_players
        self.server_socket = None
        self.clients = {}  # {player_id: {'socket': socket, 'addr': addr, 'username': str, 'is_spectator': bool, 'cards': list}}
        self.next_player_id = 0
        self.game_started = False
        self.lock = threading.Lock()
        self.running = False
        self.auto_accept = auto_accept  # 测试用：自动接受所有玩家
        
    def start(self):
        """启动服务器"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True
        print(f'\033[0;32mServer started on {self.host}:{self.port}\033[0m')
        print(f'\033[0;36mLocal IP: {get_local_ip()}\033[0m')
        # 在后台线程获取公网IP，避免阻塞启动
        def show_public_ip():
            public_ip = get_public_ip()
            if public_ip:
                print(f'\033[0;36mPublic IP: {public_ip}\033[0m')
        threading.Thread(target=show_public_ip, daemon=True).start()
        print(f'\033[0;33mWaiting for players... (Max {self.max_players} players)\033[0m')
        
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                # 新连接处理
                thread = threading.Thread(target=self._handle_new_client, args=(client_socket, addr))
                thread.daemon = True
                thread.start()
            except Exception as e:
                if self.running:
                    print(f'\033[0;31mError accepting connection: {e}\033[0m')
    
    def stop(self):
        """停止服务器"""
        self.running = False
        with self.lock:
            for client_info in self.clients.values():
                try:
                    client_info['socket'].close()
                except:
                    pass
            self.clients.clear()
        if self.server_socket:
            self.server_socket.close()
        print('\033[0;33mServer stopped.\033[0m')
    
    def _recv_msg(self, client_socket):
        """接收消息（以\n为分隔符）"""
        try:
            data = b''
            while True:
                chunk = client_socket.recv(1)
                if not chunk:
                    return None
                if chunk == b'\n':
                    break
                data += chunk
            return data.decode('utf-8').strip()
        except:
            return None
    
    def _send_msg(self, client_socket, msg):
        """发送消息（添加\n作为分隔符）"""
        try:
            client_socket.sendall((msg + '\n').encode('utf-8'))
            return True
        except:
            return False
    
    def _broadcast(self, msg, exclude_id=None, spectators_only=False, players_only=False):
        """广播消息给所有客户端"""
        with self.lock:
            for pid, client_info in self.clients.items():
                if pid == exclude_id:
                    continue
                if spectators_only and not client_info.get('is_spectator', False):
                    continue
                if players_only and client_info.get('is_spectator', False):
                    continue
                self._send_msg(client_info['socket'], msg)
    
    def _handle_new_client(self, client_socket, addr):
        """处理新客户端连接"""
        try:
            # 接收初始命令
            data = self._recv_msg(client_socket)
            if not data:
                client_socket.close()
                return
            
            parts = data.split(' ', 1)
            if len(parts) < 2:
                self._send_msg(client_socket, 'error Invalid command')
                client_socket.close()
                return
            
            cmd, username = parts[0], parts[1]
            
            if cmd == 'join':
                self._handle_join(client_socket, addr, username)
            elif cmd == 'peek':
                self._handle_spectator_join(client_socket, addr, username)
            else:
                self._send_msg(client_socket, 'error Unknown command')
                client_socket.close()
        except Exception as e:
            print(f'\033[0;31mError handling new client: {e}\033[0m')
            try:
                client_socket.close()
            except:
                pass
    
    def _handle_join(self, client_socket, addr, username):
        """处理玩家加入请求"""
        with self.lock:
            if self.game_started:
                self._send_msg(client_socket, 'error Game already started')
                client_socket.close()
                return
            
            if len([c for c in self.clients.values() if not c.get('is_spectator', False)]) >= self.max_players:
                self._send_msg(client_socket, 'error Room is full')
                client_socket.close()
                return
            
            player_id = self.next_player_id
            self.next_player_id += 1
            
            # 发送pending状态
            self._send_msg(client_socket, f'pending {player_id}')
        
        # 等待管理员确认（在锁外进行以避免阻塞）
        try:
            if self.auto_accept:
                accepted = True
            else:
                accepted = __server_joining__(client_socket, addr, username)
        except:
            accepted = False
        
        with self.lock:
            if not self.running or self.game_started:
                self._send_msg(client_socket, 'error Server is no longer accepting players')
                client_socket.close()
                return
            
            if accepted:
                self.clients[player_id] = {
                    'socket': client_socket,
                    'addr': addr,
                    'username': username,
                    'is_spectator': False,
                    'cards': []
                }
                self._send_msg(client_socket, f'accept {player_id}')
                print(f'\033[0;32mPlayer {player_id} ({username}) joined from {addr[0]}:{addr[1]}\033[0m')
                
                # 检查是否满员
                player_count = len([c for c in self.clients.values() if not c.get('is_spectator', False)])
                if player_count >= self.max_players:
                    self._start_game()
            else:
                self._send_msg(client_socket, f'reject {player_id}')
                client_socket.close()
                print(f'\033[0;33mPlayer {player_id} ({username}) rejected\033[0m')
    
    def _handle_spectator_join(self, client_socket, addr, username):
        """处理旁观者加入请求"""
        with self.lock:
            player_id = self.next_player_id
            self.next_player_id += 1
            
            self.clients[player_id] = {
                'socket': client_socket,
                'addr': addr,
                'username': username,
                'is_spectator': True,
                'cards': []
            }
            self._send_msg(client_socket, f'accept {player_id}')
            print(f'\033[0;36mSpectator {player_id} ({username}) joined from {addr[0]}:{addr[1]}\033[0m')
    
    def _start_game(self):
        """开始游戏"""
        self.game_started = True
        self._broadcast('start')
        print('\033[0;32mGame started!\033[0m')
    
    def send_turn(self, player_id):
        """发送轮到某玩家出牌"""
        self._broadcast(f'turn {player_id}')
    
    def send_play(self, player_id, remaining_cards, played_cards):
        """发送玩家出牌信息
        played_cards: list of Card objects
        """
        card_count = len(played_cards)
        card_strs = [str(c) for c in played_cards]
        msg = f'play {player_id} {remaining_cards} {card_count}'
        if card_strs:
            msg += ' ' + ' '.join(card_strs)
        self._broadcast(msg)
    
    def broadcast_chat(self, player_id, message, is_spectator=False):
        """广播聊天消息（旁观者消息对玩家和房主不可见）"""
        msg = f'chat {player_id} {message}'
        if is_spectator:
            # 只发送给其他旁观者
            self._broadcast(msg, spectators_only=True)
        else:
            # 发送给所有人
            self._broadcast(msg)
    
    def kick_player(self, player_id):
        """踢出玩家（仅限旁观者）"""
        with self.lock:
            if player_id not in self.clients:
                return False
            client_info = self.clients[player_id]
            if not client_info.get('is_spectator', False):
                return False  # 不能踢出普通玩家
            
            self._send_msg(client_info['socket'], f'kick {player_id}')
            client_info['socket'].close()
            del self.clients[player_id]
            print(f'\033[0;33mSpectator {player_id} ({client_info["username"]}) was kicked\033[0m')
            return True
    
    def player_to_spectator(self, player_id):
        """玩家转为旁观者（认输）"""
        with self.lock:
            if player_id not in self.clients:
                return False
            self.clients[player_id]['is_spectator'] = True
            self.clients[player_id]['cards'] = []
        self._broadcast(f'peek {player_id}')
        return True
    
    def remove_player(self, player_id):
        """移除玩家（断开连接）"""
        with self.lock:
            if player_id not in self.clients:
                return
            client_info = self.clients[player_id]
            try:
                self._send_msg(client_info['socket'], f'leave {player_id}')
                client_info['socket'].close()
            except:
                pass
            del self.clients[player_id]
            print(f'\033[0;33mPlayer {player_id} ({client_info["username"]}) left\033[0m')
    
    def get_player_count(self):
        """获取当前玩家数（不含旁观者）"""
        with self.lock:
            return len([c for c in self.clients.values() if not c.get('is_spectator', False)])
    
    def get_spectator_count(self):
        """获取旁观者数量"""
        with self.lock:
            return len([c for c in self.clients.values() if c.get('is_spectator', False)])
    
    def get_all_players(self):
        """获取所有玩家信息"""
        with self.lock:
            return {pid: {
                'username': info['username'],
                'is_spectator': info.get('is_spectator', False),
                'addr': info['addr']
            } for pid, info in self.clients.items()}
