
from __future__ import annotations

import os
import json
import logging
from dataclasses import dataclass


_logger = logging.getLogger(__name__)
CONFIG_EXTENSION = '.actor.json'


@dataclass
class Actor:

    @classmethod
    def find(cls, path: str) -> Actor | None:
        """Finds an actor given a file path."""
        if not os.path.exists(path) or os.path.isfile(path):
            return Actor.find(os.path.dirname(path))
        config_files = [name for name in os.listdir(path) if name.endswith(CONFIG_EXTENSION)]
        if len(config_files) > 1:
            _logger.warning(f'More than one config file found: {config_files}')
            return None
        if len(config_files) == 1:
            return Actor(os.path.join(path, config_files[0]))
        if os.path.dirname(path) == path:
            return None
        return Actor.find(os.path.dirname(path))

    @classmethod
    def in_directory(self, directory: str) -> list[Actor]:
        """Finds all actors in a given directory."""
        actors = []
        for root, dirs, files in os.walk(directory):
            for filename in files:
                if not filename.endswith(CONFIG_EXTENSION):
                    continue
                filepath = os.path.join(root, filename)
                actors.append(Actor(filepath))
        return actors

    def __init__(self, filepath: str, data: dict[str, any] = None):
        self._filepath = filepath
        self._directory = os.path.dirname(filepath)
        if data is None:
            with open(filepath, 'r') as openfile:
                self._data = json.load(openfile)
        else:
            self._data = data

    def get(self, key: str):
        if key not in self._data:
            raise KeyError(f'Key "{key}" is not defined')
        return self._data[key]

    @property
    def skeleton_fbx(self):
        return os.path.abspath(os.path.join(self._directory, self.get('skeleton_fbx')))

    @property
    def skeleton_hkx(self):
        return os.path.abspath(os.path.join(self._directory, self.get('skeleton_hkx')))

    @property
    def skeleton_nif(self):
        return os.path.abspath(os.path.join(self._directory, self.get('skeleton_nif')))

    @property
    def skeleton_le_hkx(self):
        return os.path.abspath(os.path.join(self._directory, self.get('skeleton_le_hkx')))

    @property
    def animations_fbx(self):
        return os.path.abspath(os.path.join(self._directory, self.get('animations_fbx')))

    @property
    def animations_hkx(self):
        return os.path.abspath(os.path.join(self._directory, self.get('animations_hkx')))

    def get_animation(self, animation: str):
        return os.path.abspath(os.path.join(self.animations, animation))

    @property
    def blender_rig(self):
        return os.path.abspath(os.path.join(self._directory, self.get('blender_rig')))

    @property
    def blender_import_mapping(self):
        return self.get('blender_import_mapping')

    @property
    def blender_export_mapping(self):
        return self.get('blender_export_mapping')

    @property
    def maya_rig(self):
        return os.path.join(self._directory, self.get('maya_rig'))

    @property
    def maya_import_mapping(self):
        return self.get('maya_import_mapping')