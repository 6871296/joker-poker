from time import sleep
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.unocard_class import *
from lib.uno_cardset_creator import *
from lib.uno_supports import *
from random import shuffle

def pcnt_i():
    pcnt=int(input('Players count: '))
    if pcnt>0:
        return pcnt
    else:
        print('\033[0;31mThere has to be at least 1 player!')
        sleep(1.5)
        print('\033[2J')
        return pcnt_i()

def run():
    pcnt=pcnt_i()
    print("\033[2J\033[0mGranting cards...")
    deck=NewUnoCardset()
    shuffle(deck)
    players=[[]]*pcnt
    for i in range(pcnt):
        for _ in range(7):
            players[i].append(pick_card(deck))
    
    

if __name__=='__main__':
    run()