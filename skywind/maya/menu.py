
from maya import mel
import maya.cmds as cmds

from skywind.maya.commands import open_animation
from skywind.maya.commands import import_animation_tags


SKYRIM_MENU = "skywindMenu"


def create_skywind_menu():

    # Don't create menu in batch mode
    if cmds.about(batch=True):
        return

    # Delete the menu if it exists
    if cmds.menu(SKYRIM_MENU, exists=True):
        cmds.deleteUI(SKYRIM_MENU)

    # Create the main "Skywind" menu in Maya's main menu bar
    if not cmds.menu(SKYRIM_MENU, exists=True):
        parent_menu = cmds.menu(
            SKYRIM_MENU,
            label='Skywind',
            tearOff=True,
            parent=mel.eval("$retvalue = $gMainWindow;"),
        )

    # Add a menu item labeled "Open Animation"
    cmds.menuItem(label='Open Animation', parent=parent_menu, command=open_animation)
    cmds.menuItem(label='Import Animation Tags', parent=parent_menu, command=import_animation_tags)
