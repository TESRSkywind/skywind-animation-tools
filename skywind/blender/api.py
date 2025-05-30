
import contextlib

import bpy
from ..core import ckcmd



def import_animation():

    skeleton_hkx = r'C:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition\Data\meshes\actors\alit\character assets\skeleton_le.hkx'
    skeleton_nif = r'C:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition\Data\meshes\actors\alit\character assets\skeleton.nif'
    animation = r'C:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition\Data\meshes\actors\alit\animations\attack1.fbx'
    control_rig = r'C:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition\Data\meshes\actors\alit\character assets\skeleton.blend'
    skeleton_fbx = r'C:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition\Data\meshes\actors\alit\character assets\skeleton.fbx'

    # if animation.endswith('.hkx'):
    #     animation_fbx = animation.replace('.hkx', '.fbx')
    #     ckcmd.exportanimation(skeleton_hkx, animation, animation_fbx)
    #     animation = animation_fbx


    # skeleton_fbx = skeleton_hkx.replace('.hkx', '.fbx')
    # ckcmd.export_rig(skeleton_hkx, skeleton_nif, skeleton_fbx)

    # Import Control Rig
    # bpy.ops.wm.open_mainfile(filepath=control_rig)
    bpy.ops.scene.new(type='EMPTY')
    # bpy.ops.import_scene.fbx(filepath=animation)
    bpy.ops.import_scene.fbx(filepath=skeleton_fbx, global_scale=100)


    with bpy.data.libraries.load(control_rig) as (data_from, data_to):
        files = []
        for obj in data_from.objects:
            files.append({'name': obj})
        bpy.ops.wm.append(directory=control_rig + '\\Object\\', files=files)

def import_rig():
    print('import rig')