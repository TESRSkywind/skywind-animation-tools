
import bpy

from ..fbx.tags import Tag


SOURCE_PATH_PROPERTY_NAME = 'sourcePath'


def save_source_path_to_object(object: str, filepath: str):
    object[SOURCE_PATH_PROPERTY_NAME] = filepath


def load_source_path_from_object(object: str) -> str | None:
    return object.get(SOURCE_PATH_PROPERTY_NAME)


def _get_frame_rate():
    scene = bpy.data.scenes[0]  # Access the first scene (default)
    fps = scene.render.fps
    fps_base = scene.render.fps_base
    frame_rate = fps / fps_base
    return frame_rate


def save_tags_to_object(object: str, tags: list[Tag]):

    # Ensure the armature has an action (to store animation data)
    if object.animation_data is None:
        object.animation_data_create()
    if object.animation_data.action is None:
        object.animation_data.action = bpy.data.actions.new(name=f"{object.name}_Action")
    action = object.animation_data.action

    for tag in tags:

        for time, label in tag.keyframes:

            property_name = f'{tag.node}::{tag.name}::{label}'
            if property_name not in object:
                object[property_name] = 0.0

            # Data path for the custom property
            data_path = f'["{property_name}"]'

            # Create or get the F-Curve for the property
            fcurve = action.fcurves.find(data_path)
            if fcurve is None:
                fcurve = action.fcurves.new(data_path=data_path, index=0)

            # Set the keyframe
            frame = time * _get_frame_rate()
            key = fcurve.keyframe_points.insert(frame=frame, value=0.0)
            key.interpolation = 'LINEAR'


def load_tags_from_object(object: str) -> list[Tag]:

    tags_by_id = {}  # Dict to avoid duplicates: (node, name, label) -> Tag

    # Ensure the object has animation data and an action
    if object.animation_data is None or object.animation_data.action is None:
        return []

    action = object.animation_data.action
    frame_rate = _get_frame_rate()

    # Regex to parse custom property names in the format: "node::tag_name::label"
    pattern = re.compile(r'^(.*?)::(.*?)::(.*?)$')

    for fcurve in action.fcurves:
        data_path = fcurve.data_path
        if not data_path.startswith('["') or not data_path.endswith('"]'):
            continue

        property_name = data_path[2:-2]  # Strip [" and "]
        match = pattern.match(property_name)
        if not match:
            continue

        node, tag_name, label = match.groups()
        tag_id = (node, tag_name)

        if tag_id not in tags_by_id:
            tag = Tag(node, tag_name)
            tags_by_id[tag_id] = tag
        else:
            tag = tags_by_id[tag_id]

        # Extract time from keyframes
        for key in fcurve.keyframe_points:
            time = key.co.x / frame_rate
            tag.keyframes.append((time, label))

    return list(tags_by_id.values())