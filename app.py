from lib.gameclass import Game as game
from games.settings import run as settings_run
from games.fight_the_landlord import run as ftl_run
from games.ftl_online_server import run as ftl_server_run
from games.ftl_online_client import run as ftl_client_run
from games.catch_the_red_ace import run as cra_run
from simple_term_menu import TerminalMenu

menu = [
    "Fight the Landlord",
    "Fight the Landlord (Online Server)",
    "Fight the Landlord (Online Client)",
    "Catch the Red Ace"
    "Settings",
    "Quit"
]

while True:
    print('\033[2J\033[0;1;31mJOKER POKER')
    print()

    # 设置选中项的样式
    c = TerminalMenu(
        menu,
        title='Choose a game:',
        menu_cursor="\033[0;32m ➤ \033[0;1;92m",
    ).show()

    # 处理Quit选项
    if menu[c] == "Quit":
        print('\033[2J\033[0mGoodbye!')
        break

    games = {
        'Settings': game(settings_run, 'settings'),
        'Fight the Landlord': game(ftl_run, 'fight_the_landlord'),
        'Fight the Landlord (Online Server)': game(ftl_server_run, 'ftl_online_server'),
        'Fight the Landlord (Online Client)': game(ftl_client_run, 'ftl_online_client'),
        #'Catch the Red Ace':game(cra_run,'catch_the_red_ace')
    }

    print('\033[2J')
    games[menu[c]].run()