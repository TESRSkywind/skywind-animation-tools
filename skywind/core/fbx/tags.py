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


def _get_existing_anim_layer(scene):
    """
    Returns the first existing animation layer in the scene,
    or None if none exists.
    """
    anim_stack_count = scene.GetSrcObjectCount(fbx.FbxCriteria.ObjectType(fbx.FbxAnimStack.ClassId))
    if anim_stack_count == 0:
        return None

    anim_stack = scene.GetSrcObject(fbx.FbxCriteria.ObjectType(fbx.FbxAnimStack.ClassId), 0)
    layer_count = anim_stack.GetMemberCount(fbx.FbxCriteria.ObjectType(fbx.FbxAnimLayer.ClassId))

    if layer_count == 0:
        return None

    return anim_stack.GetMember(fbx.FbxCriteria.ObjectType(fbx.FbxAnimLayer.ClassId), 0)


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
            _logger.debug('Finding node %s', tag.node)
            node = _find_node_by_name(root_node, tag.node)
            _logger.debug('Found node %s', node)

            for i in range(node.GetNodeAttributeCount()):
                prop = node.GetNodeAttributeByIndex(i)
                if prop.GetName() == tag.name:
                    _logger.info(f"Enum property '{tag.name}' already exists on node '{node.GetName()}'.")
                    break
            else:
                enum_type = fbx.FbxEnumDT
                prop = fbx.FbxProperty.Create(node, enum_type, tag.name)
                prop.ModifyFlag(fbx.FbxPropertyFlags.EFlags.eAnimatable, True)
                prop.ModifyFlag(fbx.FbxPropertyFlags.EFlags.eUserDefined, True)
                _logger.info(f"Enum property '{tag.name}' created.")

            # Add missing labels
            current_labels = _get_enum_labels(prop)
            expected_labels = set([value for key, value in tag.keyframes])
            for label in expected_labels:
                if label not in current_labels:
                    _logger.info('Adding missing label %s', label)
                    prop.AddEnumValue(label)
                    current_labels.append(label)

            anim_curve = _get_anim_curve(prop)
            if anim_curve is None:
                _logger.info('Adding missing animation curve for %s', tag.name)
                anim_layer = _get_existing_anim_layer(scene)
                anim_curve_node = prop.GetCurveNode(anim_layer, True)
                if anim_curve_node is None:
                    raise RuntimeError('Failed to create animation curve node')
                anim_curve = anim_curve_node.CreateCurve(f'{anim_curve_node.GetName()}Curve', 0)
                if anim_curve is None:
                    raise RuntimeError('Failed to create animation curve')
                _logger.info('Created %s', anim_curve.GetName())
            else:
                _logger.info('Found anim curve %s', anim_curve.GetName())

            _logger.info('Setting keyframes on %s', anim_curve.GetName())
            anim_curve.KeyModifyBegin()
            anim_curve.KeyClear()
            for frame, value in tag.keyframes:
                time = fbx.FbxTime()
                time.SetSecondDouble(frame)
                index, last = anim_curve.KeyAdd(time)
                _logger.debug('Keying %s on frame %s for %s', value, frame, anim_curve.GetName())
                anim_curve.KeySet(
                    index, time, current_labels.index(value),
                    fbx.FbxAnimCurveDef.EInterpolationType.eInterpolationConstant
                )
            anim_curve.KeyModifyEnd()
            _logger.info('Finished setting keyframes on %s', anim_curve.GetName())

        _logger.info('Saving %s', out_path)
        exporter.Export(scene)

    finally:
        exporter.Destroy()
        fbx_manager.Destroy()


if __name__ == '__main__':
    # filepath = r'C:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition\Data\meshes\actors\alit\animations\runforward.fbx'
    # filepath = r'C:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition\Data\meshes\actors\sabrecat\animations\attack1_test.fbx'
    # out_path = r'C:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition\Data\meshes\actors\sabrecat\animations\attack1_test2.fbx'
    # tags = load_animation_tags(filepath)
    # tags.append(Tag('NPC_s_Root_s__ob_Root_cb_', 'hkSoundPlay.NPCSabreCat', keyframes=[(0.9333333404195011, 'Attack')]))
    # for tag in tags:
    #     print(tags)

    tags = [Tag(node='NPC_s_Root_s__ob_Root_cb_', name='hkweapon', keyframes=[(0.4, 'Swing')]), Tag(node='NPC_s_Root_s__ob_Root_cb_', name='hkHit', keyframes=[(0.5, 'Frame')]), Tag(node='NPC_s_Root_s__ob_Root_cb_', name='hkSoundPlay.NPCSabreCat', keyframes=[(0.4, 'Attack')]), Tag(node='NPC_s_Root_s__ob_Root_cb_', name='hkFoot', keyframes=[(0.6333333333333333, 'Front'), (0.8666666666666667, 'Front'), (0.7, 'Back')])]

    filepath = r'C:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition\Data\resources\animation\guar\animations\attackpowerforward_short.fbx'
    out_path = r'C:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition\Data\resources\animation\guar\animations\test.fbx'
    # out_path = filepath.replace('.fbx', '_out.fbx')
    save_animation_tags(filepath, tags, out_path)
    tags = load_animation_tags(out_path)
    for tag in tags:
        print(tags)