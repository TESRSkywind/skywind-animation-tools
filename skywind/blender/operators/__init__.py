
import logging

import bpy

from .save_changes import *
from .open_animation import *
from .publish_animation import *


_logger = logging.getLogger(__name__)


def register():
    for subclass in bpy.types.Operator.__subclasses__():
        if subclass.__name__.startswith('SKYWIND_OT_'):
            _logger.info('Registering %s', subclass.__name__)
            subclass.bl_idname = f'skywind.{subclass.__name__.replace("SKYWIND_OT_", "")}'
            bpy.utils.register_class(subclass)


def unregister():
    for subclass in bpy.types.Operator.__subclasses__():
        if subclass.__name__.startswith('SKYWIND_OT_'):
            _logger.info('Unregistering %s', subclass.__name__)
            bpy.utils.unregister_class(subclass)