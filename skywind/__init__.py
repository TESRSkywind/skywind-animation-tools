"""Blender add-on initialization."""

from .blender import startup


def register():
    startup.register()


def unregister():
    startup.unregister()
