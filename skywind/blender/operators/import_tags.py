
import os
import logging

import bpy
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty, CollectionProperty

from ...core.preferences import get_last_dir, set_last_dir
from ...core.blender.metadata import save_tags_to_object, save_source_path_to_object
from ...core.fbx.tags import load_animation_tags


_logger = logging.getLogger(__name__)


class SKYWIND_OT_import_tags(Operator):
    bl_label = "Import Animation Tags"
    bl_description = "Import animation tags from an FBX file onto a selected armature"

    filepath: StringProperty(
        name="File Path",
        description="Filepath used for importing the animation",
        subtype='FILE_PATH',
        options={'HIDDEN', 'SKIP_SAVE'}
    )
    files: CollectionProperty(
        name="File Path",
        type=bpy.types.PropertyGroup
    )
    filter_glob: StringProperty(
        default="*.fbx",
        options={'HIDDEN'},
    )

    def invoke(self, context, event):

        # Check for selected armature
        obj = context.active_object
        if obj is None or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "No armature selected. Operator cancelled.")
            return {'CANCELLED'}
        self.armature = obj

        self.filepath = get_last_dir()
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        if self.files:
            for file in self.files:
                filepath = os.path.join(os.path.dirname(self.filepath), file.name)
                self.report({'INFO'}, f"Opening: {filepath}")
                import_animation_tags(filepath, self.armature)
                self.report({'INFO'}, f"Opened: {filepath}")
            set_last_dir(self.filepath)
        else:
            self.report({'WARNING'}, "No file(s) selected")
        return {'FINISHED'}


def import_animation_tags(filepath: str, armature: bpy.types.Armature):
    tags = load_animation_tags(filepath)
    if tags:
        _logger.info('Saving %s tags to %s', len(tags), armature.name)
        save_tags_to_object(armature, tags)
    else:
        _logger.info('No tags to save')


class SKYWIND_OT_set_source_file(Operator):
    bl_label = "Set Source File"
    bl_description = "Sets the source FBX file of a selected armature"

    filepath: StringProperty(
        name="File Path",
        description="Filepath used for importing the animation",
        subtype='FILE_PATH',
        options={'HIDDEN', 'SKIP_SAVE'}
    )
    files: CollectionProperty(
        name="File Path",
        type=bpy.types.PropertyGroup
    )
    filter_glob: StringProperty(
        default="*.fbx",
        options={'HIDDEN'},
    )

    def invoke(self, context, event):

        # Check for selected armature
        obj = context.active_object
        if obj is None or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "No armature selected. Operator cancelled.")
            return {'CANCELLED'}
        self.armature = obj

        self.filepath = get_last_dir()
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        if self.files:
            for file in self.files:
                filepath = os.path.join(os.path.dirname(self.filepath), file.name)
                self.report({'INFO'}, f"Opening: {filepath}")
                set_source_file(self.armature, filepath)
                self.report({'INFO'}, f"Opened: {filepath}")
            set_last_dir(self.filepath)
        else:
            self.report({'WARNING'}, "No file(s) selected")
        return {'FINISHED'}

    def open(self, filepath: str):
        set_source_file(filepath)


def set_source_file(armature: bpy.types.Armature, filepath: str):
    tags = load_animation_tags(filepath)
    if tags:
        _logger.info('Saving %s tags to %s', len(tags), armature.name)
        save_tags_to_object(armature, tags)
    else:
        _logger.info('No tags to save')
    save_source_path_to_object(armature, filepath)