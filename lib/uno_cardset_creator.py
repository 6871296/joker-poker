# 优诺牌生成程序 🃏

from unocard_class import *

def NewUnoCardset():

    RED    = UnoColor.RED
    YELLOW = UnoColor.YELLOW
    GREEN  = UnoColor.GREEN
    BLUE   = UnoColor.BLUE
    BLACK  = UnoColor.BLACK

    colors = [
        RED,
        YELLOW,
        GREEN,
        BLUE
    ]

    digits  = [str(i) for i in range(10)]
    actions = ['  ⃠', '⇆', '+2']
    wilds   = ['❖', '+4']

    uno_deck = []

    for bg in colors:
        for d in digits:
            count = 1 if d == '0' else 2
            for _ in range(count):
                uno_deck.append(UnoCard(bg,d))

    for bg in colors:
        for a in actions:
            for _ in range(2):
                uno_deck.append(UnoCard(bg,a))

    for w in wilds:
        for _ in range(4):
            uno_deck.append(UnoCard(BLACK,w))

    for _ in range(4):
        uno_deck.append(UnoCard(BLACK,'□'))

    return uno_deck