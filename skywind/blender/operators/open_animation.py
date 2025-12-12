
import os
import logging

import bpy
from bpy.props import StringProperty, BoolProperty, CollectionProperty
from bpy.types import Operator

from ...core.actor import Actor
from ...core.preferences import get_last_dir, set_last_dir
from ...core.blender.metadata import save_tags_to_object, save_source_path_to_object
from ...core.blender.fbx import import_fbx
from ...core.fbx.tags import load_animation_tags
from ...core.blender.armature import copy_armature_in_world_space, bake_animation


__all__ = ['SKYWIND_OT_open_animation', 'SKYWIND_OT_open_animation_debug', 'SKYWIND_OT_new_file']
_logger = logging.getLogger(__name__)


def append_scene(filepath: str) -> list:
    _logger.debug('Appending scene: %s', filepath)
    imported_objects = []

    # Load and merge collections
    with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
        _logger.debug(data_from.collections)
        data_to.collections = data_from.collections

    for imported_col in data_to.collections:
        bpy.context.scene.collection.children.link(imported_col)
        for obj in imported_col.objects:
            imported_objects.append(obj)
        for obj in imported_col.objects:
            if obj.type == 'ARMATURE':
                break
        else:
            imported_col.hide_viewport = True
            imported_col.hide_render = True

    _logger.debug('Imported objects: %s', imported_objects)
    return imported_objects


def find_skeleton(objects: list):
    skeletons = []
    for object in objects:
        if object.type == 'ARMATURE':
            skeletons.append(object)
    if len(skeletons) == 0:
        raise RuntimeError('No skeletons found.')
    if len(skeletons) > 1:
        raise RuntimeError('More than one skeleton found.')
    return skeletons[0]


def _frame_animation(skeleton):
    keyframes = set()
    for fcurve in skeleton.animation_data.action.fcurves:
        for keyframe_point in fcurve.keyframe_points:
            keyframes.add(int(keyframe_point.co.x))
    bpy.context.scene.frame_start = min(keyframes)
    bpy.context.scene.frame_end = max(keyframes)


class OpenAnimationMixin:

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
        self.filepath = get_last_dir()
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        if self.files:
            for file in self.files:
                filepath = os.path.join(os.path.dirname(self.filepath), file.name)
                self.report({'INFO'}, f"Opening: {filepath}")
                self.open(filepath)
                self.report({'INFO'}, f"Opened: {filepath}")
            set_last_dir(self.filepath)
        else:
            self.report({'WARNING'}, "No file(s) selected")
        return {'FINISHED'}

    def open(self, filepath: str):
        raise NotImplemented


class SKYWIND_OT_open_animation(Operator, OpenAnimationMixin):
    bl_label = "Open Animation"
    bl_description = "Open a Skywind animation"

    def open(self, filepath: str):
        open_animation(filepath)


class SKYWIND_OT_open_animation_debug(Operator, OpenAnimationMixin):
    bl_idname = "skywind.open_animation_debug"
    bl_label = "Open Animation (Debug)"
    bl_description = "Open and Debug a Skywind animation"

    def open(self, filepath: str):
        open_animation(filepath, debug=True)


class SKYWIND_OT_new_file(Operator):
    bl_label = "Open Animation"
    bl_description = "Open a Skywind animation"

    def invoke(self, context, event):
        _logger.info('Invoking animation')
        return bpy.ops.wm.read_homefile('INVOKE_DEFAULT', use_empty=True)

    def execute(self, context):
        bpy.ops.skywind.open_animation('INVOKE_DEFAULT')
        return {'FINISHED'}


def create_empty_scene(name: str = 'Scene'):
    new_scene = bpy.data.scenes.new(name=name)
    bpy.context.window.scene = new_scene
    current_scene = bpy.context.scene
    scenes_to_remove = [scene for scene in bpy.data.scenes if scene != current_scene]
    for scene in scenes_to_remove:
        bpy.data.scenes.remove(scene)
    return new_scene


def import_animation_tags(animation_fbx: str, object: any):
    tags = load_animation_tags(animation_fbx)

    # Ensure the armature has an action (to store animation data)
    if object.animation_data is None:
        object.animation_data_create()
    if object.animation_data.action is None:
        object.animation_data.action = bpy.data.actions.new(name=f"{object.name}_Action")
    action = object.animation_data.action

    for tag in tags:

        for time, label in tag.keyframes:

            property_name = f'{tag.node}::{tag.name}::{label}'
            if property_name not in object:
                object[property_name] = 0.0

            # Data path for the custom property
            data_path = f'["{property_name}"]'

            # Create or get the F-Curve for the property
            fcurve = action.fcurves.find(data_path)
            if fcurve is None:
                fcurve = action.fcurves.new(data_path=data_path, index=0)

            # Set the keyframe
            frame = time * _get_frame_rate()
            key = fcurve.keyframe_points.insert(frame=frame, value=0.0)
            key.interpolation = 'LINEAR'


def open_animation(animation_file: str, debug: bool = False):
    _logger.info('Opening file: %s', animation_file)

    to_cleanup = []
    actor = Actor.find(animation_file)

    # animation_fbx = actor.get_animation(animation_name)
    animation_fbx = animation_file
    bpy.ops.wm.read_homefile(use_empty=True)

    # Import Export Skeleton
    skeleton_fbx_objects = import_fbx(actor.skeleton_fbx, global_scale=100)
    to_cleanup.extend(skeleton_fbx_objects)
    export_skeleton = find_skeleton(skeleton_fbx_objects)

    # Import Animation Skeleton
    animation_fbx_objects = import_fbx(
        animation_fbx, global_scale=100, use_custom_props=True, use_custom_props_enum_as_string=True,
        anim_offset=0
    )
    to_cleanup.extend(animation_fbx_objects)
    animation_skeleton = find_skeleton(animation_fbx_objects)

    # Import Control Rig
    control_rig_objects = append_scene(actor.blender_rig)
    control_skeleton = find_skeleton(control_rig_objects)

    world_animation_skeleton = copy_armature_in_world_space(export_skeleton, use_pose_bones=True)
    world_control_skeleton = copy_armature_in_world_space(control_skeleton, use_pose_bones=True)

    to_constrain = []
    for control_bone in world_control_skeleton.pose.bones:
        if control_bone.name not in actor.blender_import_mapping:
            continue
        control_name = control_bone.name
        bone_name = actor.blender_import_mapping[control_bone.name]
        is_root = bone_name == 'NPC_s_Root_s__ob_Root_cb_'

        # Constrain world control to world bone, with offsets maintained
        bpy.context.view_layer.update()  # Ensure the dependency graph is updated
        control = world_control_skeleton.pose.bones[control_name]
        constraint = control.constraints.new(type='CHILD_OF')
        constraint.target = world_animation_skeleton
        if not is_root:
            constraint.subtarget = bone_name

        # Constrain world control to matching control
        bpy.context.view_layer.update()  # Ensure the dependency graph is updated
        control = control_skeleton.pose.bones[control_name]
        constraint = control.constraints.new(type='COPY_TRANSFORMS')
        constraint.target = world_control_skeleton
        constraint.subtarget = control_name
        to_constrain.append(bone_name)

    # Constrain animation bones to world animation bones
    for bone_name in to_constrain:
        bpy.context.view_layer.update()  # Ensure the dependency graph is updated
        is_root = bone_name == 'NPC_s_Root_s__ob_Root_cb_'
        bpy.context.view_layer.update()  # Ensure the dependency graph is updated
        control = world_animation_skeleton if is_root else world_animation_skeleton.pose.bones[bone_name]
        constraint = control.constraints.new(type='COPY_TRANSFORMS')
        constraint.target = animation_skeleton
        if not is_root:
            constraint.subtarget = bone_name

    if debug:
        return

    # Frame the timeline
    _frame_animation(animation_skeleton)

    # Bake animation onto control rig
    bake_animation(control_skeleton, actor.blender_import_mapping.keys())

    # Delete skeletons
    for item in to_cleanup:
        bpy.data.objects.remove(item, do_unlink=True)
    bpy.data.objects.remove(world_control_skeleton, do_unlink=True)
    bpy.data.objects.remove(world_animation_skeleton, do_unlink=True)

    # Save animation tags
    tags = load_animation_tags(animation_fbx)
    if tags:
        _logger.info('Saving %s tags to %s', len(tags), control_skeleton)
        save_tags_to_object(control_skeleton, tags)
    else:
        _logger.info('No tags to save')

    # Save source file name
    save_source_path_to_object(control_skeleton, animation_fbx)

    # Save scene
    file_name = os.path.basename(animation_fbx).split('.')[0]
    blender_path = os.path.join(os.path.dirname(animation_fbx), f'{file_name}.blend')
    bpy.ops.wm.save_as_mainfile(filepath=blender_path)


def import_rig():
    print('import rig')