
import os
import logging
import winreg
import contextlib

import bpy
import mathutils
from bpy.props import StringProperty, BoolProperty, CollectionProperty
from bpy_extras.io_utils import ImportHelper
from bpy.types import Operator

from ...core import ckcmd
from ...core.actor import Actor


__all__ = ['SKYWIND_OT_open_animation', 'SKYWIND_OT_open_animation_debug', 'SKYWIND_OT_new_file']
_logger = logging.getLogger(__name__)


@contextlib.contextmanager
def view_3d_context():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                with bpy.context.temp_override(window=window, area=area):
                    yield
                break


@view_3d_context()
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


@view_3d_context()
def import_fbx(fbx_file: str, **kwargs) -> list:
    existing_objects = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=fbx_file, **kwargs)
    return [obj for obj in bpy.data.objects if obj not in existing_objects]


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


@view_3d_context()
def _bake_animation(skeleton, bone_names):
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
        bake_types={'POSE'}
    )
    bpy.ops.object.mode_set(mode='OBJECT')


REG_PATH = r"Software\SkywindAnimation"
REG_KEY = "LastDirectory"


def get_last_dir():
    try:
        registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(registry_key, REG_KEY)
        winreg.CloseKey(registry_key)
        return value
    except FileNotFoundError:
        pass
    return os.path.expanduser("~")


def set_last_dir(path):
    _logger.debug('Saving last directory: %s', path)
    winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH)
    registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_WRITE)
    winreg.SetValueEx(registry_key, REG_KEY, 0, winreg.REG_SZ, path)
    winreg.CloseKey(registry_key)


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


def open_animation(animation_file: str, debug: bool = False):
    _logger.info('Opening file: %s', animation_file)

    to_cleanup = []
    actor = Actor.find(animation_file)

    # animation_fbx = actor.get_animation(animation_name)
    animation_fbx = animation_file
    bpy.ops.wm.read_homefile(use_empty=True)

    # Import Animation Skeleton
    animation_fbx_objects = import_fbx(animation_fbx, global_scale=100, use_custom_props=True, use_custom_props_enum_as_string=True)
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
    _bake_animation(control_skeleton, actor.blender_import_mapping.keys())

    # Delete skeletons
    for item in to_cleanup:
        bpy.data.objects.remove(item, do_unlink=True)
    bpy.data.objects.remove(world_control_skeleton, do_unlink=True)
    bpy.data.objects.remove(world_animation_skeleton, do_unlink=True)

    # Save scene
    file_name = os.path.basename(animation_fbx).split('.')[0]
    blender_path = os.path.join(os.path.dirname(animation_fbx), f'{file_name}.blend')
    bpy.ops.wm.save_as_mainfile(filepath=blender_path)


def import_rig():
    print('import rig')