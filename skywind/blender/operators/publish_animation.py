
import os
import logging
import time

import bpy
from bpy.props import StringProperty, BoolProperty, CollectionProperty
from bpy.types import Operator

from ...core.preferences import get_last_dir, set_last_dir
from ...core.fbx.tags import load_animation_tags, save_animation_tags
from ...core.blender.fbx import import_fbx, export_fbx_animation
from ...core.blender.metadata import load_tags_from_object, load_source_path_from_object
from ...core.blender.armature import copy_armature_in_world_space, bake_animation
from ...core.blender.mixins import ActorOperatorMixin


__all__ = ['SKYWIND_OT_publish_animation', 'SKYWIND_OT_publish_scene']
_logger = logging.getLogger(__name__)
ROOT_BONE_NAME = 'NPC_s_Root_s__ob_Root_cb_'


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


REG_PATH = r"Software\SkywindAnimation"
REG_KEY = "LastDirectory"


class SKYWIND_OT_publish_animation(Operator, ActorOperatorMixin):
    bl_label = "Publish Animation"
    bl_description = "Publish a Skywind animation"


    filepath: StringProperty(
        name="File Path",
        description="Filepath used for exporting the animation",
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
        self.actor_armature = self.get_scene_actor()
        if self.actor_armature is None:
            return {'CANCELLED'}
        self.filepath = get_last_dir()
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        if self.files:
            for file in self.files:
                filepath = os.path.join(os.path.dirname(self.filepath), file.name)
                self.report({'INFO'}, f"Publishing: {filepath}")
                actor, armature = self.actor_armature
                publish_control_rig_animation(
                    armature,
                    filepath,
                    actor.skeleton_fbx,
                    actor.blender_export_mapping
                )
                self.report({'INFO'}, f"Published: {filepath}")
            set_last_dir(self.filepath)
        else:
            self.report({'WARNING'}, "No file(s) selected")
        return {'FINISHED'}


class SKYWIND_OT_publish_scene(Operator, ActorOperatorMixin):
    bl_label = "Publish Scene"
    bl_description = "Publish all Skywind animations in the scene"

    def execute(self, context):
        self.actor_armatures = self.get_scene_actors()
        if len(self.actor_armatures) == 0:
            return {'CANCELLED'}
        for actor, armature in self.actor_armatures:
            filepath = load_source_path_from_object(armature)
            publish_control_rig_animation(
                armature,
                filepath,
                actor.skeleton_fbx,
                actor.blender_export_mapping
            )
            self.report({'INFO'}, f"Published: {filepath}")
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


def publish_control_rig_animation(
        control_skeleton: bpy.types.Armature, animation_file: str, skeleton_fbx: str,
        blender_export_mapping: dict[str, str]
):
    _logger.info('Publishing file: %s', animation_file)

    to_cleanup = []

    # Import Export Skeleton
    skeleton_fbx_objects = import_fbx(skeleton_fbx, global_scale=100)
    to_cleanup.extend(skeleton_fbx_objects)
    export_skeleton = find_skeleton(skeleton_fbx_objects)

    world_export_skeleton = copy_armature_in_world_space(export_skeleton, name='WorldExportSkeleton')
    world_control_skeleton = copy_armature_in_world_space(control_skeleton, name='WorldControlSkeleton')


    to_constrain = []
    for control in world_control_skeleton.pose.bones:
        if control.name not in blender_export_mapping:
            continue
        control_name = control.name
        bone_name = blender_export_mapping[control_name]
        is_root = bone_name == ROOT_BONE_NAME

        # Constrain the world export skeleton to the world control skeleton
        bpy.context.view_layer.update()  # Ensure the dependency graph is updated
        if is_root:
            constraint = world_export_skeleton.constraints.new(type='CHILD_OF')
            constraint.target = world_control_skeleton
            constraint.subtarget = control_name
        else:
            pose_bone = world_export_skeleton.pose.bones[bone_name]
            constraint = pose_bone.constraints.new(type='CHILD_OF')
            constraint.target = world_control_skeleton
            constraint.subtarget = control_name

        bpy.context.view_layer.update()  # Ensure the dependency graph is updated
        if is_root:
            constraint = export_skeleton.constraints.new(type='COPY_TRANSFORMS')
            constraint.target = world_export_skeleton
        else:
            export_bone = export_skeleton.pose.bones[bone_name]
            constraint = export_bone.constraints.new(type='COPY_TRANSFORMS')
            constraint.target = world_export_skeleton
            constraint.subtarget = bone_name
        to_constrain.append(control_name)

    for control_name in to_constrain:
        bpy.context.view_layer.update()  # Ensure the dependency graph is updated
        control = world_control_skeleton.pose.bones[control_name]
        constraint = control.constraints.new(type='COPY_TRANSFORMS')
        constraint.target = control_skeleton
        constraint.subtarget = control_name

    # Bake animation onto control rig
    to_bake = [bone for bone in blender_export_mapping.values() if bone != ROOT_BONE_NAME]
    bake_animation(export_skeleton, to_bake)

    # Delete skeletons
    bpy.data.objects.remove(world_control_skeleton, do_unlink=True)
    bpy.data.objects.remove(world_export_skeleton, do_unlink=True)

    # Export the animation
    _logger.info('Exporting %s', animation_file)
    export_fbx_animation(export_skeleton, animation_file, global_scale=0.01)

    # Cleanup export skeleton
    _logger.info('Removing export skeleton')
    for item in to_cleanup:
        bpy.data.objects.remove(item, do_unlink=True)

    # Save animation tags
    tags = load_tags_from_object(control_skeleton)
    if tags:
        _logger.info('Exporting animation tags')
        save_animation_tags(animation_file, tags)
        _logger.info('Exported animation tags')


def import_rig():
    print('import rig')