
import os

from ..core import startup
from . import menu


def register():
    startup.initialize()

    menu.register()


def unregister():
    menu.unregister()