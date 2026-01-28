
import os
import logging
import shutil
import tempfile

from skywind.core.actor import Actor
from skywind.ck.api import convert_animation_fbx_to_hkx


_logger = logging.getLogger(__name__)


def batch_import_animations(directory: str):

    for actor in Actor.in_directory(directory):
        for filename in os.listdir(actor.animations_fbx):
            if not filename.endswith('.fbx'):
                continue
            filepath = os.path.join(actor.animations_fbx, filename)
            output_file = os.path.join(
                actor.animations_hkx, os.path.basename(filepath).replace('.fbx', '.hkx')
            )
            _logger.info('Importing animation from %s', filepath)
            for required_file in (actor.skeleton_le_hkx, filepath, os.path.dirname(output_file)):
                if not os.path.exists(required_file):
                    raise FileNotFoundError(f'{required_file} does not exist')
            convert_animation_fbx_to_hkx(actor.skeleton_le_hkx, filepath, os.path.dirname(output_file))
            _logger.info('Imported animation to %s', output_file)


if __name__ == '__main__':

    directory = None
    while directory is None:
        input_text = input('Enter a directory: ')
        if not os.path.exists(input_text):
            print('Directory does not exist. Please try again.')
            continue
        directory = input_text

    batch_import_animations(directory)