"""Blender Skywind menu"""

import bpy
from .operators import *
MENU_COMMANDS = [
    SKYWIND_OT_open_animation.__name__,
    SKYWIND_OT_open_animation_debug.__name__,
    SKYWIND_OT_publish_animation.__name__,
    SKYWIND_OT_publish_animation_debug.__name__
]


class SKYWIND_MT_menu(bpy.types.Menu):
    bl_label = "Skywind"

    def draw(self, context):
        for command in MENU_COMMANDS:
            self.layout.operator(command)


def menu_draw(self, context):
   self.layout.menu(SKYWIND_MT_menu.__name__)


def register():
    bpy.utils.register_class(SKYWIND_MT_menu)
    bpy.types.TOPBAR_MT_editor_menus.append(menu_draw)


def unregister():
    bpy.utils.unregister_class(SKYWIND_MT_menu)
    bpy.types.TOPBAR_MT_editor_menus.remove(menu_draw)