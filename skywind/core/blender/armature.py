

import logging

import bpy
import mathutils

from .contexts import view_3d_context

_logger = logging.getLogger(__name__)


def _get_bone_matrix(bone: bpy.types.Bone) -> mathutils.Matrix:
    if isinstance(bone, bpy.types.PoseBone):
        return bone.matrix
    else:
        mat = bone.matrix.to_4x4()
        mat.translation = mathutils.Vector(bone.head_local)
        return mat


@view_3d_context()
def copy_armature_in_world_space(armature: bpy.types.Armature, use_pose_bones: bool = False) -> bpy.types.Armature:

    intermediate_rig_name = 'IntermediateRig'
    intermediate_rig = bpy.data.armatures.new(intermediate_rig_name)
    intermediate_obj = bpy.data.objects.new(intermediate_rig_name, intermediate_rig)
    bpy.context.collection.objects.link(intermediate_obj)
    bpy.context.view_layer.objects.active = intermediate_obj

    # Enter edit mode to create bones
    bpy.ops.object.mode_set(mode='EDIT')
    bones = armature.pose.bones if use_pose_bones else armature.data.bones
    for bone in bones:
        ctrl_bone = bones[bone.name]
        world_matrix = armature.matrix_world @ _get_bone_matrix(ctrl_bone)
        new_bone = intermediate_rig.edit_bones.new(bone.name)
        new_bone.head = world_matrix @ mathutils.Vector((0, 0, 0))
        new_bone.tail = world_matrix @ mathutils.Vector((0, 1, 0))
        new_bone.align_roll(world_matrix @ mathutils.Vector((0, 0, 1)) - new_bone.head)
    bpy.ops.object.mode_set(mode='OBJECT')

    return intermediate_obj


@view_3d_context()
def bake_animation(skeleton: bpy.types.Armature, bone_names: list[str]):
    _logger.debug('Baking skeleton: %s' % skeleton)
    bpy.context.view_layer.objects.active = skeleton

    skeleton.select_set(True)
    bpy.context.view_layer.objects.active = skeleton

    bpy.ops.object.mode_set(mode='POSE')
    for pose_bone in skeleton.pose.bones:
        pose_bone.bone.select = False
    for bone_name in bone_names:
        skeleton.data.bones[bone_name].select = True

    bpy.ops.nla.bake(
        frame_start=int(bpy.context.scene.frame_start),
        frame_end=int(bpy.context.scene.frame_end),
        only_selected=True,
        visual_keying=True,
        clear_constraints=False,
        use_current_action=True,
        bake_types={'POSE', 'OBJECT'}
    )
    bpy.ops.object.mode_set(mode='OBJECT')