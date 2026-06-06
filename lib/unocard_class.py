from enum import Enum as enum


class UnoColor(enum):
    BLACK='\033[0;1m'
    RED='\033[0;31m'
    BLUE='\033[0;34m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    
    def __str__(self):
        return self.value
    
'''
    0='0'
    1='1'
    2='2'
    3='3'
    4='4'
    5='5'
    6='6'
    7='7'
    8='8'
    9='9'
    P2='+2'
    REV='⇆'
    MUTE=' ⃠'
    WILD='❖'
    P4='+4'
    CUSTOM='✍'
    HANDWASH='🙌'
'''

class UnoCard:
    def __init__(self,color:str,name:str):
        self.color=color
        self.name=name
    def __str__(self):
        return self.name
    def info(self):
        print(self.color+self.name)
        
from typing import List
cardset=List[UnoCard]

def playable(last:UnoCard,this:UnoCard)->bool:
    return this.color==UnoColor.BLACK or this.color==last.color or this.name==last.name

class UnoConst(enum):
    R0=UnoCard(UnoColor.RED,'0')
    R1=UnoCard(UnoColor.RED,'1')
    R2=UnoCard(UnoColor.RED,'2')
    R3=UnoCard(UnoColor.RED,'3')
    R4=UnoCard(UnoColor.RED,'4')
    R5=UnoCard(UnoColor.RED,'5')
    R6=UnoCard(UnoColor.RED,'6')
    R7=UnoCard(UnoColor.RED,'7')
    R8=UnoCard(UnoColor.RED,'8')
    R9=UnoCard(UnoColor.RED,'9')
    RP=UnoCard(UnoColor.RED,'+2')
    RR=UnoCard(UnoColor.RED,'⇆')
    RM=UnoCard(UnoColor.RED,' ⃠')
    
    G0=UnoCard(UnoColor.GREEN,'0')
    G1=UnoCard(UnoColor.GREEN,'1')
    G2=UnoCard(UnoColor.GREEN,'2')
    G3=UnoCard(UnoColor.GREEN,'3')
    G4=UnoCard(UnoColor.GREEN,'4')
    G5=UnoCard(UnoColor.GREEN,'5')
    G6=UnoCard(UnoColor.GREEN,'6')
    G7=UnoCard(UnoColor.GREEN,'7')
    G8=UnoCard(UnoColor.GREEN,'8')
    G9=UnoCard(UnoColor.GREEN,'9')
    GP=UnoCard(UnoColor.GREEN,'+2')
    GR=UnoCard(UnoColor.GREEN,'⇆')
    GM=UnoCard(UnoColor.GREEN,' ⃠')
    
    B0=UnoCard(UnoColor.BLUE,'0')
    B1=UnoCard(UnoColor.BLUE,'1')
    B2=UnoCard(UnoColor.BLUE,'2')
    B3=UnoCard(UnoColor.BLUE,'3')
    B4=UnoCard(UnoColor.BLUE,'4')
    B5=UnoCard(UnoColor.BLUE,'5')
    B6=UnoCard(UnoColor.BLUE,'6')
    B7=UnoCard(UnoColor.BLUE,'7')
    B8=UnoCard(UnoColor.BLUE,'8')
    B9=UnoCard(UnoColor.BLUE,'9')
    BP=UnoCard(UnoColor.BLUE,'+2')
    BR=UnoCard(UnoColor.BLUE,'⇆')
    BM=UnoCard(UnoColor.BLUE,' ⃠')
    
    Y0=UnoCard(UnoColor.YELLOW,'0')
    Y1=UnoCard(UnoColor.YELLOW,'1')
    Y2=UnoCard(UnoColor.YELLOW,'2')
    Y3=UnoCard(UnoColor.YELLOW,'3')
    Y4=UnoCard(UnoColor.YELLOW,'4')
    Y5=UnoCard(UnoColor.YELLOW,'5')
    Y6=UnoCard(UnoColor.YELLOW,'6')
    Y7=UnoCard(UnoColor.YELLOW,'7')
    Y8=UnoCard(UnoColor.YELLOW,'8')
    Y9=UnoCard(UnoColor.YELLOW,'9')
    YP=UnoCard(UnoColor.YELLOW,'+2')
    YR=UnoCard(UnoColor.YELLOW,'⇆')
    YM=UnoCard(UnoColor.YELLOW,' ⃠')
    
    WILD=UnoCard(UnoColor.BLACK,'❖')
    P4=UnoCard(UnoColor.BLACK,'+4')
    CUSTOM=UnoCard(UnoColor.BLACK,'✍')
    HANDWASH=UnoCard(UnoColor.BLACK,'🙌')