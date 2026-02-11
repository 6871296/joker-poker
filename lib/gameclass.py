class Game:
    def __init__(self,gameInitFunc,gameName):
        self.InitFunc=gameInitFunc
        self.name=gameName
    def run(self):
        self.InitFunc()