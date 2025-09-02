

import site
site.addsitedir(r'E:\Projects\Source\Skywind\skywind_animation_tools\skywind\site-packages\3.11')
import fbx  # noqa
import sys

import fbx
import sys

def is_joint_node(node):
    # FBX SDK considers joints as skeleton nodes
    attr = node.GetNodeAttribute()
    return attr is not None

def is_property_animated(fbx_property):
    anim_curve_count = fbx_property.GetSrcObjectCount(fbx.FbxCriteria.ObjectType(fbx.FbxAnimCurveNode.ClassId))
    for i in range(anim_curve_count):
        curve_node = fbx_property.GetSrcObject(fbx.FbxCriteria.ObjectType(fbx.FbxAnimCurveNode.ClassId), i)
        if curve_node:
            for c in range(curve_node.GetCurveCount(0)):
                if curve_node.GetCurve(0, c):
                    return True
    return False

def find_animated_properties_on_joints(node):
    animated_props = []

    if is_joint_node(node):
        prop = node.GetFirstProperty()
        while prop.IsValid():
            if prop.GetFlag(fbx.FbxPropertyFlags.EFlags.eUserDefined):
                if is_property_animated(prop, node):
                    animated_props.append((node.GetName(), prop.GetName()))
            prop = node.GetNextProperty(prop)

    # Recurse into children
    for i in range(node.GetChildCount()):
        animated_props.extend(find_animated_properties_on_joints(node.GetChild(i)))

    return animated_props

def load_fbx_scene(fbx_manager, file_path):
    importer = fbx.FbxImporter.Create(fbx_manager, "")
    status = importer.Initialize(file_path, -1, fbx_manager.GetIOSettings())

    if not status:
        print("Failed to initialize FBX importer.")
        return None

    scene = fbx.FbxScene.Create(fbx_manager, "Scene")
    importer.Import(scene)
    importer.Destroy()
    return scene

def main(file_path):
    fbx_manager = fbx.FbxManager.Create()
    ios = fbx.FbxIOSettings.Create(fbx_manager, fbx.IOSROOT)
    fbx_manager.SetIOSettings(ios)

    scene = load_fbx_scene(fbx_manager, file_path)
    if scene is None:
        print("Could not load FBX scene.")
        return

    root_node = scene.GetRootNode()
    if not root_node:
        print("Empty FBX scene.")
        return

    animated_props = find_animated_properties_on_joints(root_node)

    if animated_props:
        print("Animated Properties on Joints:")
        for node_name, prop_name in animated_props:
            print(f"Joint: {node_name}, Property: {prop_name}")
    else:
        print("No animated properties found on joints.")

    # Cleanup
    fbx_manager.Destroy()

if __name__ == "__main__":
    main(r'C:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition\Data\meshes\actors\alit\animations\runforward.fbx')