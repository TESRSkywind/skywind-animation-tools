
import os
import site

from ..core import startup
from . import menu
from . import api


def register():
    startup.initialize()

    api.register()
    menu.register()


def unregister():
    api.unregister()
    menu.unregister()