"""Module for reading tags from a Skywind FBX file."""
import dataclasses
import logging

import fbx

_logger = logging.getLogger(__name__)
__all__ = ['load_animation_tags']


def _get_anim_curve(fbx_property: fbx.FbxProperty) -> fbx.FbxAnimCurveNode | None:
    anim_curve_count = fbx_property.GetSrcObjectCount(fbx.FbxCriteria.ObjectType(fbx.FbxAnimCurveNode.ClassId))
    for i in range(anim_curve_count):
        curve_node = fbx_property.GetSrcObject(fbx.FbxCriteria.ObjectType(fbx.FbxAnimCurveNode.ClassId), i)
        if curve_node:
            for c in range(curve_node.GetCurveCount(0)):
                if curve_node.GetCurve(0, c):
                    return curve_node.GetCurve(0, c)
    return None


def _get_enum_labels(prop: fbx.FbxProperty) -> list[str]:
    labels = []
    enum_count = prop.GetEnumCount()
    for i in range(enum_count):
        labels.append(prop.GetEnumValue(i))
    return labels


def _get_anim_curve_keyframes(anim_curve: fbx.FbxAnimCurveNode) -> list[tuple[float, float]]:
    keyframes = []
    for i in range(anim_curve.KeyGetCount()):
        key = anim_curve.KeyGet(i)
        time_sec = key.GetTime().GetSecondDouble()
        value = key.GetValue()
        keyframes.append((time_sec, value))
    return keyframes


@dataclasses.dataclass
class Tag:
    node: str
    name: str
    keyframes: list[tuple[float, str]]


def _find_tags(node: fbx.FbxNode) -> list[Tag]:
    tags = []

    prop = node.GetFirstProperty()
    while prop.IsValid():
        if prop.GetFlag(fbx.FbxPropertyFlags.EFlags.eUserDefined):
            anim_curve = _get_anim_curve(prop)
            if anim_curve:
                keyframes = _get_anim_curve_keyframes(anim_curve)
                labels = _get_enum_labels(prop)
                keyframes = [(time, labels[int(value)]) for time, value in keyframes]
                tags.append(Tag(node.GetName(), str(prop.GetName()), keyframes))
        prop = node.GetNextProperty(prop)

    # Recurse into children
    for i in range(node.GetChildCount()):
        tags.extend(_find_tags(node.GetChild(i)))

    return tags


def _load_fbx_scene(fbx_manager: fbx.FbxManager, file_path: str) -> fbx.FbxScene:
    importer = fbx.FbxImporter.Create(fbx_manager, "")
    try:
        status = importer.Initialize(file_path, -1, fbx_manager.GetIOSettings())

        if not status:
            _logger.warning("Failed to initialize FBX importer.")
            return None

        scene = fbx.FbxScene.Create(fbx_manager, "Scene")
        importer.Import(scene)
        return scene
    finally:
        importer.Destroy()


def load_animation_tags(file_path: str) -> list[Tag] | None:
    fbx_manager = fbx.FbxManager.Create()
    try:
        ios = fbx.FbxIOSettings.Create(fbx_manager, fbx.IOSROOT)
        fbx_manager.SetIOSettings(ios)

        scene = _load_fbx_scene(fbx_manager, file_path)
        if scene is None:
            _logger.warning("Could not load FBX scene.")
            return None

        root_node = scene.GetRootNode()
        if not root_node:
            _logger.warning("Empty FBX scene.")
            return None

        return _find_tags(root_node)

    finally:
        fbx_manager.Destroy()


def _find_node_by_name(node: fbx.FbxNode, name: str) -> fbx.FbxNode | None:
    if node.GetName() == name:
        return node
    for i in range(node.GetChildCount()):
        found = _find_node_by_name(node.GetChild(i), name)
        if found:
            return found
    return None


def load_animation_tags(file_path: str) -> list[Tag] | None:
    fbx_manager = fbx.FbxManager.Create()
    try:
        ios = fbx.FbxIOSettings.Create(fbx_manager, fbx.IOSROOT)
        fbx_manager.SetIOSettings(ios)

        scene = _load_fbx_scene(fbx_manager, file_path)
        if scene is None:
            _logger.warning("Could not load FBX scene.")
            return None

        root_node = scene.GetRootNode()
        if not root_node:
            _logger.warning("Empty FBX scene.")
            return None

        return _find_tags(root_node)

    finally:
        fbx_manager.Destroy()


def save_animation_tags(file_path: str, tags: list[Tag], out_path: str | None = None):
    out_path = out_path or file_path
    fbx_manager = fbx.FbxManager.Create()
    exporter = fbx.FbxExporter.Create(fbx_manager, "")
    try:
        ios = fbx.FbxIOSettings.Create(fbx_manager, fbx.IOSROOT)
        fbx_manager.SetIOSettings(ios)

        scene = _load_fbx_scene(fbx_manager, file_path)
        if scene is None:
            _logger.warning("Could not load FBX scene.")
            return None

        root_node = scene.GetRootNode()
        if not root_node:
            _logger.warning("Empty FBX scene.")
            return None

        if not exporter.Initialize(out_path, -1, fbx_manager.GetIOSettings()):
            _logger.exception("Failed to save FBX:", exporter.GetStatus().GetErrorString())
            return

        for tag in tags:
            node = _find_node_by_name(root_node, tag.node)

            for i in range(node.GetNodeAttributeCount()):
                prop = node.GetNodeAttributeByIndex(i)
                if prop.GetName() == tag.name:
                    _logger.info(f"Enum property '{tag.name}' already exists on node '{node.GetName()}'.")
                    break
            else:
                enum_type = fbx.FbxEnumDT
                prop = fbx.FbxProperty.Create(node, enum_type, tag.name)
                _logger.info(f"Enum property '{tag.name}' created.")

            # Add missing labels
            current_labels = _get_enum_labels(prop)
            expected_labels = set([value for key, value in tag.keyframes])
            for label in expected_labels:
                if label not in current_labels:
                    prop.AddEnumValue(label)
                    current_labels.append(label)

            anim_curve = _get_anim_curve(prop)

            anim_curve.KeyModifyBegin()
            anim_curve.KeyClear()
            for frame, value in tag.keyframes:
                time = fbx.FbxTime()
                time.SetSecondDouble(frame)
                index, last = anim_curve.KeyAdd(time)
                anim_curve.KeySet(
                    index, time, current_labels.index(value),
                    fbx.FbxAnimCurveDef.EInterpolationType.eInterpolationConstant
                )
            anim_curve.KeyModifyEnd()

        exporter.Export(scene)

    finally:
        exporter.Destroy()
        fbx_manager.Destroy()


if __name__ == '__main__':
    filepath = r'C:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition\Data\meshes\actors\alit\animations\runforward.fbx'
    tags = load_animation_tags(filepath)
    for tag in tags:
        print(tags)
    out_path = filepath.replace('.fbx', '_out.fbx')
    save_animation_tags(filepath, tags, out_path)
    tags = load_animation_tags(out_path)
    for tag in tags:
        print(tags)