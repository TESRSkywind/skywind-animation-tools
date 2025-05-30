
import os

from ..core import startup
from . import menu


def register():
    startup.initialize()

    import bqt
    os.environ['BQT_DISABLE_WRAP'] = '1'
    bqt.register()

    menu.register()


def unregister():
    menu.unregister()