
from __future__ import annotations

import os
import json


CONFIG_EXTENSION = '.config.json'


class Actor:

    @classmethod
    def find(cls, path: str) -> Actor:
        if os.path.isfile(path):
            return Actor.find(os.path.dirname(path))
        config_files = [name for name in os.listdir(path) if name.endswith(CONFIG_EXTENSION)]
        if len(config_files) > 1:
            raise RuntimeError(f'More than one config file found: {config_files}')
        if len(config_files) == 1:
            return Actor(os.path.join(path, config_files[0]))
        return Actor.find(os.path.dirname(path))

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
        return os.path.join(self._directory, self.get('skeleton_fbx'))

    @property
    def skeleton_hkx(self):
        return os.path.join(self._directory, self.get('skeleton_hkx'))

    @property
    def skeleton_nif(self):
        return os.path.join(self._directory, self.get('skeleton_nif'))

    @property
    def skeleton_le_hkx(self):
        return os.path.join(self._directory, self.get('skeleton_le_hkx'))

    @property
    def animations(self):
        return os.path.join(self._directory, self.get('animations'))

    def get_animation(self, animation: str):
        return os.path.join(self.animations, animation)

    @property
    def blender_rig(self):
        return os.path.join(self._directory, self.get('blender_rig'))

    @property
    def blender_import_mapping(self):
        return self.get('blender_import_mapping')

    @property
    def maya_rig(self):
        return os.path.join(self._directory, self.get('maya_rig'))

    @property
    def maya_import_mapping(self):
        return self.get('maya_import_mapping')