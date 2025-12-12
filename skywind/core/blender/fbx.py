
import os

import bpy
from ...core.blender.contexts import view_3d_context


__all__ = ['import_fbx', 'export_fbx_animation']


@view_3d_context()
def import_fbx(fbx_file: str, **kwargs) -> list:
    existing_objects = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=fbx_file, **kwargs)
    return [obj for obj in bpy.data.objects if obj not in existing_objects]


@view_3d_context()
def export_fbx_animation(armature: bpy.types.Armature, fbx_file: str, **kwargs):

    # Deselect everything
    bpy.ops.object.select_all(action='DESELECT')

    # Select the armature
    armature.select_set(True)

    # Make the armature the active object
    bpy.context.view_layer.objects.active = armature

    # Ensure directory exists
    os.makedirs(os.path.dirname(fbx_file), exist_ok=True)

    # Export to FBX
    bpy.ops.export_scene.fbx(
        filepath=fbx_file,
        use_selection=True,
        apply_unit_scale=True,
        add_leaf_bones=False,
        bake_anim=True,
        bake_anim_use_all_actions=False,
        bake_anim_force_startend_keying=True,
        bake_anim_step=1.0,
        bake_anim_use_nla_strips=False,
        bake_anim_simplify_factor=0.0,     # Keep every keyframe for accuracy
        object_types={'ARMATURE'},  # Specify object types to export
        **kwargs
    )