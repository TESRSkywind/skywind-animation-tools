"""Blender Skywind menu"""

import bpy


MENUS = [
    {'id': 'open_animation', 'label': 'Open Animation', 'command': 'skywind.blender.api.import_animation'},
    {'id': 'open_rig', 'label': 'Open Rig', 'command': 'test'},
]


def _generate_command(command_string: str):
    def inner(self, context):
        module = '.'.join(command_string.split('.')[1:-1])
        function = command_string.split('.')[-1]
        package = '.'.join(__package__.split('.')[:-1])
        formatted = f'''import {package}.{module};{package}.{module}.{function}()'''
        exec(formatted)
        return {'FINISHED'}
    return inner


MENU_COMMANDS = []
for menu_data in MENUS:
    class_name = f'SKYWIND_MT_{menu_data["id"]}'
    bl_name = f'skywind.{menu_data["id"]}'
    MENU_COMMANDS.append(type(
        f'{class_name}Menu',
        (bpy.types.Operator,),
        {
            'bl_idname': bl_name,
            'bl_label': menu_data['label'],
            'execute': _generate_command(menu_data['command'])
        }
    ))


class SKYWIND_MT_skywind(bpy.types.Menu):
    bl_label = "Skywind"

    def draw(self, context):
        for command in MENU_COMMANDS:
            self.layout.operator(command.bl_idname)


def menu_draw(self, context):
   self.layout.menu(SKYWIND_MT_skywind.__name__)


def register():
    for operator_class in MENU_COMMANDS:
        bpy.utils.register_class(operator_class)
    bpy.utils.register_class(SKYWIND_MT_skywind)
    bpy.types.TOPBAR_MT_editor_menus.append(menu_draw)


def unregister():
    for operator_class in MENU_COMMANDS:
        bpy.utils.unregister_class(operator_class)
    bpy.utils.unregister_class(SKYWIND_MT_skywind)
    bpy.types.TOPBAR_MT_editor_menus.remove(menu_draw)