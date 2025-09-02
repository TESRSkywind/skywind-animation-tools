


def initialize():
    from maya import cmds
    cmds.evalDeferred('from skywind.maya.menu import create_skywind_menu;create_skywind_menu()')
