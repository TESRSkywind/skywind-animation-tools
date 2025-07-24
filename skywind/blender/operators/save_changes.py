import bpy
import os
from bpy.types import Operator
from bpy.props import StringProperty, EnumProperty
from bpy_extras.io_utils import ImportHelper


__all__ = ['SKYWIND_OT_save_changes_dialog']


class SKYWIND_OT_save_changes_dialog(Operator, ImportHelper):
    bl_idname = "plugin.modal_dialog"
    bl_label = ""
    bl_options = {'REGISTER', 'INTERNAL'}

    # find if dialog is currently active?

    def get_cls(self):
        cls = PLUGIN_OT_modal_dialog
        return cls

    dialog_state = False

    def get_dialog_state(self) -> bool:
        return self.get_cls().dialog_state

    def set_dialog_state(self, value: bool, ) -> None:
        self.get_cls().dialog_state = value
        return None

    instance_type: bpy.props.StringProperty(default="UNDEFINED", options={'SKIP_SAVE', }, )

    def invoke(self, context, event, ):
        """decide if we'll invoke modal or dialog"""

        # launch both modal & dialog instance of this operator simultaneously
        if (self.instance_type == "UNDEFINED"):
            bpy.ops.plugin.modal_dialog('INVOKE_DEFAULT', instance_type="DIALOG", )
            bpy.ops.plugin.modal_dialog('INVOKE_DEFAULT', instance_type="MODAL", )
            return {'FINISHED'}

        # launch a dialog instance?
        if (self.instance_type == "DIALOG"):
            self.set_dialog_state(True)
            return context.window_manager.invoke_props_dialog(self)

        # launch a modal instance?
        if (self.instance_type == "MODAL"):
            self.modal_start(context)
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

        return {'FINISHED'}

    def __del__(self):
        """called when the operator has finished"""

        # some of our instances might be gone from memory,
        # therefore 'instance_type' is not available for some instance at this stage
        # not the dialog box instance tho & we need to update class status

        try:
            if (self.instance_type == "DIALOG"):
                self.set_dialog_state(False)
        except:
            pass

        return None

    def modal(self, context, event, ):
        """for modal instance"""

        # modal state only active while dialog instance is!
        if (self.get_dialog_state() == False):
            self.modal_quit(context)
            return {'FINISHED'}

        print("modal")

        return {'PASS_THROUGH'}

    def modal_start(self, context, ):
        print("modal_start")
        return None

    def modal_quit(self, context, ):
        print("modal_quit")
        return None

    def draw(self, context, ):
        """dialog box ui code"""

        self.layout.label(text="my drawing")

        return None

    def execute(self, context, ):
        """mandatory function called when user press on 'ok' """

        return {'FINISHED'}