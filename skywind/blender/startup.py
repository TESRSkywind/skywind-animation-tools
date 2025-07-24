
import os
import site

from ..core import startup
from . import menu
from . import operators


def register():
    startup.initialize()
    operators.register()
    menu.register()


def unregister():
    operators.unregister()
    menu.unregister()