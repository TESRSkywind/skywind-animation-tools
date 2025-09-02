"""Blender add-on initialization."""



def register():
    from .blender import startup
    startup.register()


def unregister():
    from .blender import startup
    startup.unregister()
