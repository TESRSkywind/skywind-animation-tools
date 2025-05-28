import bpy


class BlenderMenu(bpy.types.Menu):
    bl_label = "Skywind"

    def draw(self, context):
        layout = self.layout
        layout.operator("object.select_all", text="Select All").action = 'SELECT'
        layout.separator()
        layout.menu("MY_MT_custom_submenu", text="My Submenu")


def menu_draw(self, context):
   self.layout.menu("BlenderMenu")


def register():
    bpy.utils.register_class(BlenderMenu)
    bpy.types.TOPBAR_MT_editor_menus.append(menu_draw)


def unregister():
    bpy.utils.unregister_class(BlenderMenu)
    bpy.types.TOPBAR_MT_editor_menus.remove(menu_draw)