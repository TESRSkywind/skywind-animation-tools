

from PySide6.QtWidgets import QMainWindow
from shiboken6 import wrapInstance
import maya.OpenMayaUI as omui


def get_main_window() -> QMainWindow:
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(main_window_ptr), QMainWindow)