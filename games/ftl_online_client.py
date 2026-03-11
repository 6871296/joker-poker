import socket
import sys
import threading
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.getip import get_local_ip
from lib.cardclass import Card as card
from lib.cardset_class import Cardset_ftl as cset
from lib.cardset_class import Cardset_type_ftl as cstype

'''
斗地主在线客户端
自动检测本机房间并加入
'''

class FTLClient:
    def __init__(self):
        self.socket = None
        self.player_id = None
        self.username = None
        self.cards = []  # 手牌
        self.is_spectator = False
        self.landlord_id = None
        self.current_turn = None
        self.last_cards = None  # 上一手出的牌
        self.running = False
        self.receive_thread = None
        self.game_started = False
        self.players_info = {}  # {player_id: {'remaining': count}}
        
    def connect(self, host, port=5555):
        """连接到服务器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            self.socket.settimeout(0.5)  # 设置超时以便可以中断
            return True
        except Exception as e:
            print(f'\033[0;31mConnection failed: {e}\033[0m')
            return False
    
    def disconnect(self):
        """断开连接"""
        self.running = False
        if self.socket:
            try:
                if self.player_id is not None:
                    self.send_msg(f'leave {self.player_id}')
                self.socket.close()
            except:
                pass
            self.socket = None
    
    def send_msg(self, msg):
        """发送消息"""
        try:
            self.socket.sendall((msg + '\n').encode('utf-8'))
            return True
        except Exception as e:
            print(f'\033[0;31mSend failed: {e}\033[0m')
            return False
    
    def recv_msg(self):
        """接收消息"""
        try:
            data = b''
            while self.running:
                try:
                    chunk = self.socket.recv(1)
                    if not chunk:
                        return None
                    if chunk == b'\n':
                        break
                    data += chunk
                except socket.timeout:
                    continue
                except:
                    return None
            return data.decode('utf-8').strip() if data else None
        except:
            return None
    
    def check_local_server(self, port=5555):
        """检查本机是否有服务器在运行"""
        try:
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_sock.settimeout(2)
            test_sock.connect(('127.0.0.1', port))
            test_sock.close()
            return True
        except:
            return False
    
    def join_game(self, username, as_spectator=False):
        """加入游戏"""
        self.username = username
        self.is_spectator = as_spectator
        cmd = 'peek' if as_spectator else 'join'
        self.send_msg(f'{cmd} {username}')
        
        # 等待响应
        while True:
            msg = self.recv_msg()
            if msg is None:
                return False
            
            parts = msg.split(' ')
            cmd = parts[0]
            
            if cmd == 'pending':
                self.player_id = int(parts[1])
                print(f'\033[0;33mWaiting for host to accept... (Your ID: {self.player_id})\033[0m')
            elif cmd == 'accept':
                self.player_id = int(parts[1])
                print(f'\033[0;32mAccepted! Your player ID is {self.player_id}\033[0m')
                if as_spectator:
                    print('\033[0;36mYou are now a spectator.\033[0m')
                return True
            elif cmd == 'reject':
                print('\033[0;31mRejected by host.\033[0m')
                return False
            elif cmd == 'error':
                print(f'\033[0;31mError: {" ".join(parts[1:])}\033[0m')
                return False
    
    def start_receive_loop(self):
        """启动接收消息的循环"""
        self.running = True
        self.receive_thread = threading.Thread(target=self._receive_loop)
        self.receive_thread.daemon = True
        self.receive_thread.start()
    
    def _receive_loop(self):
        """后台接收消息循环"""
        while self.running:
            msg = self.recv_msg()
            if msg is None:
                if self.running:
                    print('\033[0;31m\nDisconnected from server.\033[0m')
                    self.running = False
                break
            self._handle_message(msg)
    
    def _handle_message(self, msg):
        """处理服务器消息"""
        parts = msg.split(' ')
        cmd = parts[0]
        
        if cmd == 'start':
            print('\033[0;32m\n=== Game Started! ===\033[0m')
            self.game_started = True
        
        elif cmd == 'game_start':
            if len(parts) > 1:
                self.landlord_id = int(parts[1])
                if self.landlord_id == self.player_id:
                    print('\033[0;1;33m\nYou are the LANDLORD!\033[0m')
                else:
                    print(f'\033[0;33m\nPlayer {self.landlord_id} is the landlord.\033[0m')
        
        elif cmd == 'landlord_cards':
            # 显示地主底牌
            card_strs = parts[1:]
            print('\033[0;1;33m\nLandlord cards: \033[0m', end='')
            for cs in card_strs:
                c = card(cs)
                print(f'{c}{c.info()} ', end='')
            print()
        
        elif cmd == 'your_cards':
            # 接收手牌
            count = int(parts[1])
            card_strs = parts[2:2+count]
            self.cards = [card(c) for c in card_strs]
            print(f'\n\033[0;32mReceived {count} cards!\033[0m')
            self._show_cards()
        
        elif cmd == 'turn':
            player_id = int(parts[1])
            self.current_turn = player_id
            if player_id == self.player_id:
                print('\n\033[0;1;35m>>> It\'s YOUR turn! <<<!\033[0m')
            else:
                print(f'\n\033[0;35mTurn: Player {player_id}\033[0m')
        
        elif cmd == 'play':
            # play <player_id> <remaining> <count> <cards...>
            player_id = int(parts[1])
            remaining = int(parts[2])
            card_count = int(parts[3])
            self.players_info[player_id] = {'remaining': remaining}
            
            if card_count > 0:
                card_strs = parts[4:4+card_count]
                played = [card(c) for c in card_strs]
                self.last_cards = cset(played)
                print(f'\033[0;36mPlayer {player_id} played {card_count} cards:\033[0m')
                for c in played:
                    print(f'  {c}{c.info()}')
                print(f'  ({remaining} cards left)')
            else:
                print(f'\033[0;33mPlayer {player_id} passed.\033[0m')
        
        elif cmd == 'chat':
            player_id = int(parts[1])
            message = ' '.join(parts[2:])
            print(f'\033[0;36m[Chat] Player {player_id}: {message}\033[0m')
        
        elif cmd == 'new_round':
            self.last_cards = None
            print('\033[0;1;33m\n=== New Round! ===\033[0m')
        
        elif cmd == 'win':
            winner_id = int(parts[1])
            if winner_id == self.player_id:
                print('\033[0;1;32m\n=== YOU WIN! ===\033[0m')
            else:
                print(f'\033[0;1;32m\n=== Player {winner_id} wins! ===\033[0m')
            self.running = False
        
        elif cmd == 'kick':
            kicked_id = int(parts[1])
            if kicked_id == self.player_id:
                print('\033[0;31m\nYou have been kicked by the host!\033[0m')
                self.running = False
            else:
                print(f'\033[0;33mPlayer {kicked_id} was kicked.\033[0m')
        
        elif cmd == 'leave':
            left_id = int(parts[1])
            print(f'\033[0;33mPlayer {left_id} left the game.\033[0m')
        
        elif cmd == 'player_peek':
            peek_id = int(parts[1])
            print(f'\033[0;33mPlayer {peek_id} became a spectator.\033[0m')
        
        elif cmd == 'disconnect':
            disc_id = int(parts[1])
            print(f'\033[0;31mPlayer {disc_id} disconnected.\033[0m')
        
        elif cmd == 'error':
            error_msg = ' '.join(parts[1:])
            print(f'\033[0;31m[Error] {error_msg}\033[0m')
    
    def _show_cards(self):
        """显示手牌"""
        print('\n\033[0;1mYour cards:\033[0m')
        for i, c in enumerate(self.cards):
            print(f'  {i}. {c}{c.info()}')
        print()
    
    def play_cards(self, card_indices):
        """出牌"""
        if self.current_turn != self.player_id:
            print('\033[0;31mNot your turn!\033[0m')
            return False
        
        if not card_indices:  # 不出
            self.send_msg(f'play {self.player_id} {len(self.cards)} 0')
            return True
        
        # 获取要出的牌
        try:
            selected = [self.cards[i] for i in card_indices]
        except IndexError:
            print('\033[0;31mInvalid card index!\033[0m')
            return False
        
        # 验证牌型
        ocset = cset(selected)
        if ocset.playable() == cstype.UNPLAYABLE:
            print('\033[0;31mInvalid card combination!\033[0m')
            return False
        
        # 从手牌中移除
        for idx in sorted(card_indices, reverse=True):
            self.cards.pop(idx)
        
        # 发送出牌消息
        card_strs = [str(c) for c in selected]
        msg = f'play {self.player_id} {len(self.cards)} {len(selected)} ' + ' '.join(card_strs)
        self.send_msg(msg)
        return True
    
    def pass_turn(self):
        """跳过/要不起"""
        if self.current_turn != self.player_id:
            print('\033[0;31mNot your turn!\033[0m')
            return False
        self.send_msg(f'play {self.player_id} {len(self.cards)} 0')
        print('\033[0;33mYou passed.\033[0m')
        return True
    
    def send_chat(self, message):
        """发送聊天消息"""
        if len(message) > 128:
            message = message[:128]
        self.send_msg(f'chat {self.player_id} {message}')
    
    def become_spectator(self):
        """转为旁观者（认输）"""
        self.send_msg(f'peek {self.player_id}')
        self.is_spectator = True
        print('\033[0;33mYou became a spectator.\033[0m')
    
    def kick_player(self, target_id):
        """踢出玩家（仅地主可用）"""
        self.send_msg(f'kick {target_id}')


def print_help():
    """打印帮助信息"""
    print('''
\033[0;1mCommands:\033[0m
  \033[0;33m<numbers>\033[0m    - Play cards by indices (e.g., "0 2 5" to play cards #0, #2, #5)
  \033[0;33mp\033[0m or \033[0;33mpass\033[0m   - Pass/skip your turn
  \033[0;33mc <msg>\033[0m      - Send chat message (e.g., "c hello everyone")
  \033[0;33ms\033[0m or \033[0;33msurrender\033[0m - Become spectator (give up)
  \033[0;33mq\033[0m or \033[0;33mquit\033[0m     - Leave the game
  \033[0;33mh\033[0m or \033[0;33mhelp\033[0m     - Show this help
  \033[0;33mshow\033[0m         - Show your cards again
''')

def username_input():
    username = input('Enter your name: ').strip()
    if not username:
        username = f'Player{hash(time.time()) % 100000}'
    elif len(username)>=32:
        print('\033[0;31mUsername too long! (Maximum 32 chars)\033[2J')
        return username_input()
    elif len(username)<1:
        print('\033[0;31mUsername too short! (Minimum 1 char)\033[2J')
        return username_input()
    return username
        
def run():
    print('\033[2J\033[0m=== JOKER POKER - Fight The Landlord Client ===\n')
    
    client = FTLClient()
    
    # 自动检测本机服务器
    print('Checking for local server...')
    if client.check_local_server():
        print('\033[0;32mLocal server detected!\033[0m')
        host = '127.0.0.1'
    else:
        #print('\033[0;33mNo local server found.\033[0m')
        local_ip = get_local_ip()
        host = input(f'Enter server IP (default {local_ip}): ').strip()
        if not host:
            host = local_ip
    
    port_input = input('Enter server port (default 5555): ').strip()
    port = int(port_input) if port_input else 5555
    
    # 连接服务器
    print(f'\nConnecting to {host}:{port}...')
    if not client.connect(host, port):
        print('\033[0;31mFailed to connect. Exiting.\033[0m')
        return
    print('\033[0;32mConnected!\033[0m')
    time.sleep(1)
    print('\033[2J')
    
    # 输入用户名
    username=username_input()
    
    # 选择加入方式
    mode = input('\033[2JJoin as (p)layer or (s)pectator? [p]: ').strip().lower()
    as_spectator = mode == 's'
    
    # 加入游戏
    print('\nJoining game...')
    if not client.join_game(username, as_spectator):
        client.disconnect()
        return
    
    # 启动接收线程
    client.start_receive_loop()
    
    print('\n\033[0;32mWaiting for game to start...\033[0m')
    print_help()
    
    # 主循环：处理用户输入
    try:
        while client.running:
            try:
                user_input = input().strip()
            except EOFError:
                break
            
            if not user_input:
                continue
            
            parts = user_input.split(' ')
            cmd = parts[0].lower()
            
            if cmd in ['q', 'quit', 'exit']:
                break
            
            elif cmd in ['h', 'help']:
                print_help()
            
            elif cmd in ['show']:
                client._show_cards()
            
            elif cmd in ['p', 'pass']:
                client.pass_turn()
            
            elif cmd in ['s', 'surrender']:
                confirm = input('Are you sure you want to surrender? [y/N]: ').lower()
                if confirm == 'y':
                    client.become_spectator()
            
            elif cmd == 'c':
                if len(parts) < 2:
                    print('\033[0;31mUsage: c <message>\033[0m')
                else:
                    message = ' '.join(parts[1:])
                    client.send_chat(message)
            
            elif cmd.isdigit() or (len(parts) > 0 and all(p.isdigit() for p in parts)):
                # 出牌
                try:
                    indices = [int(p) for p in parts]
                    client.play_cards(indices)
                except ValueError:
                    print('\033[0;31mInvalid input. Use numbers to select cards.\033[0m')
            
            else:
                print('\033[0;31mUnknown command. Type "h" for help.\033[0m')
    
    except KeyboardInterrupt:
        print('\n\033[0;33mInterrupted.\033[0m')
    
    finally:
        print('\n\033[0;33mDisconnecting...\033[0m')
        client.disconnect()
        time.sleep(0.5)  # 等待断开
        print('\033[0;32mGoodbye!\033[0m')


if __name__ == '__main__':
    run()
