
import os
import contextlib

import bpy
import mathutils
from bpy.props import StringProperty, BoolProperty
from bpy_extras.io_utils import ImportHelper
from bpy.types import Operator

from ..core import ckcmd
from ..core.actor import Actor
from . import dialog


def _copy_skeleton_in_world_space(skeleton):

    intermediate_rig_name = 'IntermediateRig'
    intermediate_rig = bpy.data.armatures.new(intermediate_rig_name)
    intermediate_obj = bpy.data.objects.new(intermediate_rig_name, intermediate_rig)
    bpy.context.collection.objects.link(intermediate_obj)
    bpy.context.view_layer.objects.active = intermediate_obj

    # Enter edit mode to create bones
    bpy.ops.object.mode_set(mode='EDIT')
    for bone in skeleton.pose.bones:
        ctrl_bone = skeleton.pose.bones[bone.name]
        world_matrix = skeleton.matrix_world @ ctrl_bone.matrix
        new_bone = intermediate_rig.edit_bones.new(bone.name)
        new_bone.head = world_matrix @ mathutils.Vector((0, 0, 0))
        new_bone.tail = world_matrix @ mathutils.Vector((0, 1, 0))
        new_bone.align_roll(world_matrix @ mathutils.Vector((0, 0, 1)) - new_bone.head)
    bpy.ops.object.mode_set(mode='OBJECT')

    return intermediate_obj


def append_scene(filepath: str) -> list:

    imported_objects = []

    # Load and merge collections
    with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
        collections_to_import = []
        for collection in data_from.collections:
            if not bpy.data.collections.get(collection):
                collections_to_import.append(collection)
        data_to.collections = collections_to_import

    for imported_col in data_to.collections:
        if imported_col is None:
            continue
        bpy.context.scene.collection.children.link(imported_col)
        for obj in imported_col.objects:
            imported_objects.append(obj)

    with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
        data_to.objects = [obj for obj in data_from.objects if obj not in bpy.data.objects]

    for imported_object in data_to.objects:
        if imported_object is None:
            continue
        bpy.context.collection.objects.link(imported_object)
        imported_objects.append(imported_object)

    return imported_objects


def import_fbx(fbx_file: str, **kwargs) -> list:
    bpy.ops.import_scene.fbx(filepath=fbx_file, **kwargs)
    return [obj for obj in bpy.context.selected_objects]


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


def _bake_animation(skeleton):
    bpy.context.view_layer.objects.active = skeleton
    bpy.ops.nla.bake(
        frame_start=int(bpy.context.scene.frame_start),
        frame_end=int(bpy.context.scene.frame_end),
        only_selected=False,
        visual_keying=True,
        clear_constraints=False,
        use_current_action=True,
        bake_types={'POSE'}
    )


class SKYWIND_OT_open_animation(Operator, ImportHelper):
    bl_idname = "SKYWIND_OT_open_animation"
    bl_label = "Open Animation"
    filter_glob: StringProperty(default='*.fbx', options={'HIDDEN'})

    def execute(self, context):
        """Do something with the selected file(s)."""
        open_animation(self.filepath)
        return {'FINISHED'}


def open_animation(animation_file: str):
    to_cleanup = []

    actor = Actor.find(animation_file)

    # animation_fbx = actor.get_animation(animation_name)
    animation_fbx = animation_file

    # Import Animation Skeleton
    bpy.ops.scene.new(type='EMPTY')
    animation_fbx_objects = import_fbx(animation_fbx, global_scale=100)
    to_cleanup.extend(animation_fbx_objects)
    animation_skeleton = find_skeleton(animation_fbx_objects)

    # Import Export Skeleton
    skeleton_fbx_objects = import_fbx(actor.skeleton_fbx, global_scale=100)
    to_cleanup.extend(skeleton_fbx_objects)
    export_skeleton = find_skeleton(skeleton_fbx_objects)

    # Import Control Rig
    control_rig_objects = append_scene(actor.blender_rig)
    control_skeleton = find_skeleton(control_rig_objects)

    world_animation_skeleton = _copy_skeleton_in_world_space(export_skeleton)
    world_control_skeleton = _copy_skeleton_in_world_space(control_skeleton)

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

        # Constrain animation bone to world animation bone
        bpy.context.view_layer.update()  # Ensure the dependency graph is updated
        control = world_animation_skeleton if is_root else world_animation_skeleton.pose.bones[bone_name]
        constraint = control.constraints.new(type='COPY_TRANSFORMS')
        constraint.target = animation_skeleton
        if not is_root:
            constraint.subtarget = bone_name

    # Frame the timeline
    _frame_animation(animation_skeleton)

    # Bake animation onto control rig
    _bake_animation(control_skeleton)

    # Delete skeletons
    for item in to_cleanup:
        bpy.data.objects.remove(item, do_unlink=True)
    bpy.data.objects.remove(world_control_skeleton, do_unlink=True)
    bpy.data.objects.remove(world_animation_skeleton, do_unlink=True)


def import_rig():
    print('import rig')


def register():
    bpy.utils.register_class(SKYWIND_OT_open_animation.__name__)

def unregister():
    bpy.utils.unregister_class(SKYWIND_OT_open_animation.__name__)