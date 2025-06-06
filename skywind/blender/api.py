
import contextlib

import bpy
import mathutils
from ..core import ckcmd

IMPORT_MAPPING = {
    # '': 'root_jnt',
    'Spine01_jnt': 'Sabrecat__ob_pelv_cb_',
    'spine02_jnt': 'Sabrecat_Spine_ob_Spn0_cb_',
    'tail01_jnt': 'Sabrecat_Tail1_ob_Tal1_cb_',
    'tail02_jnt': 'Sabrecat_Tail2_ob_Tal2_cb_',
    'upperSpine_jnt': 'Sabrecat_Spine_ob_Spn1_cb_',
    'neck_jnt': 'Sabrecat_Spine_ob_Spn2_cb_',
    'Jaw_Jnt': 'Sabrecat_Spine_ob_Spn3_cb_',
    'tongue01_jnt': 'Sabrecat_Neck_ob_Nek0_cb_',
    'tongue02_jnt': 'Sabrecat_Neck_ob_Nek1_cb_',
    'right_hip_jnt': 'Sabrecat_RightThigh_ob_RThi_cb_',
    # 'right_knee_jnt': 'Sabrecat_RightCalf_ob_RClf_cb_',
    # 'right_ankle_jnt': 'Sabrecat_RightFoot_ob_RFot_cb_',
    'left_hip_jnt': 'Sabrecat_LeftThigh_ob_LThi_cb_',
    # 'left_knee_jnt': 'Sabrecat_LeftCalf_ob_LClf_cb_',
    # 'left_ankle_jnt': 'Sabrecat_LeftFoot_ob_LFot_cb_',

    'ctrl_foot_R': 'Sabrecat_RightToe0_ob_RT00_cb_',
    'ctrl_foot_L': 'Sabrecat_LeftToe0_ob_LT00_cb_',

    'left_knee_jnt': 'Sabrecat_LeftCalf_ob_LClf_cb_',
    'right_knee_jnt': 'Sabrecat_RightCalf_ob_RClf_cb_',
    'left_ankle_jnt': 'Sabrecat_LeftFoot_ob_LFot_cb_',
    'right_ankle_jnt': 'Sabrecat_RightFoot_ob_RFot_cb_',

    'ctrl_knee_R': 'Sabrecat_RightThigh_ob_RThi_cb_',
    'ctrl_knee_L': 'Sabrecat_LeftThigh_ob_LThi_cb_',

    'right_toe_jnt': 'Sabrecat_RightToe0_ob_RT01_cb_',
    'left_toe_jnt': 'Sabrecat_LeftToe0_ob_LT01_cb_',
    }


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


def _create_constraint(constraint_type, parent_skeleton, parent_bone_name, child_skeleton, child_bone_name):
    bpy.context.view_layer.update()  # Ensure the dependency graph is updated
    control = child_skeleton.pose.bones[child_bone_name]
    constraint = control.constraints.new(type=constraint_type)
    # constraint.name = "CopyTransformsFromControl"
    constraint.target = parent_skeleton
    constraint.subtarget = parent_bone_name
    return constraint


def _copy_transforms_constraint(source_bone, target_skeleton, target_bone):
    return _create_constraint('COPY_TRANSFORMS', source_bone, target_skeleton, target_bone)


def _child_of_constraint(source_bone, target_skeleton, target_bone):
    return _create_constraint('CHILD_OF', source_bone, target_skeleton, target_bone)


def import_animation():
    to_cleanup = []

    skeleton_hkx = r'C:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition\Data\meshes\actors\alit\character assets\skeleton_le.hkx'
    skeleton_nif = r'C:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition\Data\meshes\actors\alit\character assets\skeleton.nif'
    animation_fbx = r'C:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition\Data\meshes\actors\alit\animations\attack1.fbx'
    control_rig = r'C:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition\Data\meshes\actors\alit\character assets\skeleton.blend'
    skeleton_fbx = r'C:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition\Data\meshes\actors\alit\character assets\skeleton.fbx'

    # if animation.endswith('.hkx'):
    #     animation_fbx = animation.replace('.hkx', '.fbx')
    #     ckcmd.exportanimation(skeleton_hkx, animation, animation_fbx)
    #     animation = animation_fbx

    # skeleton_fbx = skeleton_hkx.replace('.hkx', '.fbx')
    # ckcmd.export_rig(skeleton_hkx, skeleton_nif, skeleton_fbx)

    # Import Animation Skeleton
    bpy.ops.scene.new(type='EMPTY')
    animation_fbx_objects = import_fbx(animation_fbx, global_scale=100)
    to_cleanup.extend(animation_fbx_objects)
    animation_skeleton = find_skeleton(animation_fbx_objects)
    return
    # Import Export Skeleton
    skeleton_fbx_objects = import_fbx(skeleton_fbx, global_scale=100)
    to_cleanup.extend(skeleton_fbx_objects)
    export_skeleton = find_skeleton(skeleton_fbx_objects)

    # Import Control Rig
    control_rig_objects = append_scene(control_rig)
    control_skeleton = find_skeleton(control_rig_objects)

    world_animation_skeleton = _copy_skeleton_in_world_space(export_skeleton)
    world_control_skeleton = _copy_skeleton_in_world_space(control_skeleton)

    for control_bone in world_control_skeleton.pose.bones:
        if control_bone.name not in IMPORT_MAPPING:
            continue
        control_name = control_bone.name
        bone_name = IMPORT_MAPPING[control_bone.name]

        # Constrain world control to world bone, with offsets maintained
        _create_constraint(
            'CHILD_OF',
            world_animation_skeleton, bone_name,
            world_control_skeleton, control_name
        )

        # Constrain world control to matching control
        _create_constraint(
            'COPY_TRANSFORMS',
            world_control_skeleton, control_name,
            control_skeleton, control_name
        )

        # Constrain animation bone to world animation bone
        _create_constraint(
            'COPY_TRANSFORMS',
            animation_skeleton, bone_name,
            world_animation_skeleton, bone_name
        )

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