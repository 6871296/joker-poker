def pick_card(deck:list,id:int=0):
    x=deck[id]
    deck.remove(x)
    return x