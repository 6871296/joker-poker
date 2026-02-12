#废稿
from dice import *
from time import sleep
def random_card():
    print('\033[0m',end='')
    dice_cards()
    sleep(0.25)
    print('\033[1D\033[K',end='')
        
def loading(game):
    print('\033[0;1mLoading game: \033[0;1;36m'+game,end='')
    
    