

import contextlib

import bpy


@contextlib.contextmanager
def view_3d_context():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                with bpy.context.temp_override(window=window, area=area):
                    yield
                break