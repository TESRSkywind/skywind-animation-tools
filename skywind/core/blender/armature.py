

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
def copy_armature_in_world_space(armature_obj: bpy.types.Object, use_pose_bones: bool = False,
                                 name: str = None) -> bpy.types.Object:
    intermediate_rig_name = name or 'IntermediateRig'
    intermediate_rig_data = bpy.data.armatures.new(intermediate_rig_name)
    intermediate_obj = bpy.data.objects.new(intermediate_rig_name, intermediate_rig_data)
    bpy.context.collection.objects.link(intermediate_obj)

    # Ensure the source is evaluated if using pose bones
    src_obj_eval = armature_obj

    # Enter edit mode to create bones
    bpy.context.view_layer.objects.active = intermediate_obj
    bpy.ops.object.mode_set(mode='EDIT')

    source_bones = src_obj_eval.pose.bones if use_pose_bones else src_obj_eval.data.bones

    for src_bone in source_bones:
        # Create new bone
        new_bone = intermediate_rig_data.edit_bones.new(src_bone.name)

        # Calculate World Matrix: Object World Matrix @ Bone Local Matrix
        # Note: For PoseBones use .matrix, for EditBones/DataBones use .matrix_local
        bone_local_matrix = src_bone.matrix if use_pose_bones else src_bone.matrix_local
        world_matrix = armature_obj.matrix_world @ bone_local_matrix

        # 1. Set Head (The translation part of the matrix)
        new_bone.head = world_matrix.to_translation()

        # 2. Set Tail (The head + the Y-axis direction scaled by length)
        # In Blender bones, the Y-axis points from Head to Tail
        bone_direction = world_matrix.to_quaternion() @ mathutils.Vector((0, 1, 0))
        new_bone.tail = new_bone.head + (bone_direction * src_bone.length)

        # 3. Match Roll
        # We align the new bone's Z-axis to the source bone's world-space Z-axis
        world_z_axis = world_matrix.to_quaternion() @ mathutils.Vector((0, 0, 1))
        new_bone.align_roll(world_z_axis)

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