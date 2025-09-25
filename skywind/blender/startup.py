
import os
import site

from ..core import startup


def register():
    startup.initialize()

    from . import operators
    operators.register()

    from . import menu
    menu.register()


def unregister():
    from . import operators
    operators.unregister()

    from . import menu
    menu.unregister()