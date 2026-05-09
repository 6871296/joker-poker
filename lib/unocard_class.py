from enum import Enum as enum



class UnoColor(enum):
    UNIVERSAL='\033[0;1;40m'
    RED='\033[0;41m'
    BLUE='\033[0;44m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;43m'

class UnoCard:
    def __init__(self,color:str,name:str):
        self.color=color
        self.name=name
    def __str__(self):
        return self.name
    def info(self):
        print(self.color+self.name)
