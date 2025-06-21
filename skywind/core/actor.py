
from __future__ import annotations

import os
import json


CONFIG_EXTENSION = '.config.json'


def current_data_directory() -> str:
    return r'C:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition\Data'


class Actor:

    @classmethod
    def find(cls, path: str) -> Actor:
        if os.path.isfile(path):
            return Actor.find(os.path.dirname(path))
        config_files = [name for name in os.listdir(path) if name.endswith(CONFIG_EXTENSION)]
        if len(config_files) > 1:
            raise RuntimeError(f'More than one config file found: {config_files}')
        if len(config_files) == 1:
            return Actor.load(os.path.join(path, config_files[0]))
        return Actor.find(os.path.dirname(path))

    @classmethod
    def load(cls, filepath: str) -> Actor:
        with open(filepath, 'r') as openfile:
            return Actor(json.load(openfile))

    def __init__(self, data: dict[str, any]):
        self._data = data

    def get(self, key: str):
        if key not in self._data:
            raise KeyError(f'Key "{key}" is not defined')
        return self._data[key]

    @property
    def skeleton_fbx(self):
        return os.path.join(current_data_directory(), self.get('directory'), self.get('skeleton_fbx'))

    @property
    def skeleton_hkx(self):
        return os.path.join(current_data_directory(), self.get('directory'), self.get('skeleton_hkx'))

    @property
    def skeleton_nif(self):
        return os.path.join(current_data_directory(), self.get('directory'), self.get('skeleton_nif'))

    @property
    def skeleton_le_hkx(self):
        return os.path.join(current_data_directory(), self.get('directory'), self.get('skeleton_le_hkx'))

    @property
    def animations(self):
        return os.path.join(current_data_directory(), self.get('directory'), self.get('animations'))

    def get_animation(self, animation: str):
        return os.path.join(self.animations, animation)

    @property
    def blender_rig(self):
        return os.path.join(current_data_directory(), self.get('directory'), self.get('blender_rig'))

    @property
    def blender_import_mapping(self):
        return self.get('blender_import_mapping')