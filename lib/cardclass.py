class Card:
    def __init__(self,chr:str):
        self.chr=chr
    def __str__(self):
        return self.chr
    def info(self):
        code_point = ord(self.chr)
        
        # 大小王特殊处理
        if code_point == 0x1f0cf:  # 红色大王
            return '\033[0;31mJOKER (Red)\033[0m'
        if code_point == 0x1f0df:  # 黑色小王
            return '\033[0;1mJOKER (Black)\033[0m'
            
        # 扑克牌 Unicode 范围: 0x1f0a1-0x1f0af (A-K), 0x1f0b1-0x1f0bf, 0x1f0c1-0x1f0cf, 0x1f0d1-0x1f0df
        # 格式: 0x1f0[花色][点数]
        # 花色: a=黑桃♠, b=红心♥, c=方块♦, d=梅花♣
        # 点数: 1=A, 2-10, 11=J, 12=骑士(C), 13=Q, 14=K (但通常跳过C和 knight)
        
        if 0x1f0a1 <= code_point <= 0x1f0de:
            suit_code = (code_point >> 4) & 0x0f  # 提取花色位
            rank_code = code_point & 0x0f  # 提取点数位
            
            # 花色映射
            suits = {0x0a: ('♠', '\033[0;1m'),   # 黑桃 - 白色
                     0x0b: ('♥', '\033[0;31m'),  # 红心 - 红色
                     0x0c: ('♦', '\033[0;31m'), # 方块 - 红色
                     0x0d: ('♣', '\033[0;1m')}     # 梅花 - 白色
            
            # 点数映射 (注意: 0xC 是骑士牌，现代扑克通常不用)
            ranks = {0x01: 'Ace', 0x02: '2', 0x03: '3', 0x04: '4', 0x05: '5',
                     0x06: '6', 0x07: '7', 0x08: '8', 0x09: '9', 0x0a: '10',
                     0x0b: 'Jack', 0x0d: 'Queen', 0x0e: 'King'}
            
            suit_info = suits.get(suit_code, ('Unknown', '\033[0m'))
            rank_name = ranks.get(rank_code, 'Unknown')
            
            return f'{suit_info[1]}{suit_info[0]} {rank_name}\033[0m'
        else:
            return f'\033[0mUnknown ({self.chr})\033[0m'
            