
from dataclasses import dataclass

import bpy

from ..actor import Actor
from .metadata import SOURCE_PATH_PROPERTY_NAME, load_source_path_from_object


def _find_armatures_in_scene() -> list[bpy.types.Armature]:
    actors = []
    for obj in bpy.context.scene.objects:
        if obj.type == 'ARMATURE':
            actors.append(obj)
    return actors


class ActorOperatorMixin:

    def get_scene_actors(self) -> list[tuple[Actor, bpy.types.Armature]]:

        armatures = _find_armatures_in_scene()

        actors = []
        for armature in armatures:
            source_file = load_source_path_from_object(armature)
            if source_file is None:
                self.report({'WARNING'}, f"No source file found for {armature.name}")
                continue
            actor = Actor.find(source_file)
            if actor is None:
                self.report({'WARNING'}, f"No actor found for {source_file}")
                continue
            actors.append((actor, armature))

        if len(actors) == 0:
            self.report({'WARNING'}, "No actors found")

        return actors

    def get_scene_actor(self) -> tuple[Actor, bpy.types.Armature] | None:
        actors = self.get_scene_actors()
        if len(actors) > 1:
            self.report({'WARNING'}, "Multiple actors found")
            return None
        for actor in actors:
            return actors
        return None
