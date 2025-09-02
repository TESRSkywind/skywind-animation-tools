
import os

import maya.api.OpenMaya as om2
from maya import cmds
from maya import mel
from PySide6.QtWidgets import QFileDialog

from skywind.core.log import getLogger
from skywind.core.maya.main_window import get_main_window
from skywind.core.actor import Actor

__all__ = ['open_animation']
_logger = getLogger(__name__)


def _open_file_dialog() -> str | None:
    parent = get_main_window()
    dialog = QFileDialog(parent)
    dialog.setNameFilter("FBX files (*.fbx)")
    dialog.setFileMode(QFileDialog.ExistingFile)

    if dialog.exec_():
        selected_files = dialog.selectedFiles()
        return selected_files[0]
    return None


def _import_fbx(filepath: str, update=True) -> list[str]:
    if not str(filepath).lower().endswith('.fbx'):
        raise RuntimeError('"%s" is not an fbx file.' % filepath)
    if not os.path.exists(filepath):
        raise RuntimeError('Path "%s" does not exist' % filepath)

    mObjects = []

    def addNode(mObject, *args):
        """ A function that stores all added nodes. """
        if mObject.isNull():
            return
        mObjectHandle = om2.MObjectHandle(mObject)
        if not mObjectHandle.isAlive():
            return
        if not mObjectHandle.isValid():
            return
        mObjects.append((mObjectHandle, mObject))

    # Create a callback to listen for new nodes.
    callback = om2.MDGMessage.addNodeAddedCallback(addNode, 'dependNode')
    try:
        # Import the file
        cmds.unloadPlugin('fbxmaya')
        cmds.loadPlugin('fbxmaya')
        mel.eval('FBXImportMode -v %s' % ('exmerge' if update else 'add'))
        mel.eval('FBXImportFillTimeline -v true')
        mel.eval('FBXImport -f "%s"' % filepath.replace('\\', '/'))
    finally:
        # Always remove the callback
        om2.MMessage.removeCallback(callback)

    # Convert mObjects to node names
    nodes = set()
    for mObjectHandle, mObject in mObjects:
        if mObject.isNull():
            continue
        if not mObjectHandle.isAlive():
            continue
        if not mObjectHandle.isValid():
            continue
        if mObject.hasFn(om2.MFn.kDagNode):
            name = om2.MFnDagNode(mObject).fullPathName()
        else:
            name = om2.MFnDependencyNode(mObject).name()
        if cmds.objExists(name):
            nodes.add(name)

    return list(nodes)


def open_animation(fbx_file: str | None = None, reference: bool = True):

    fbx_file = fbx_file or _open_file_dialog()
    if not fbx_file:
        return _logger.warning("No file selected.")
    actor = Actor.find(fbx_file)

    # Create a new scene
    cmds.file(newFile=True, force=True)

    # Import control rig
    rig_namespace = os.path.basename(actor.maya_rig).split('.')[0]
    rig_nodes = cmds.file(
        actor.maya_rig, i=True, type="mayaAscii", ignoreVersion=True, mergeNamespacesOnClash=False,
        options="v=0;", pr=True, returnNewNodes=True, namespace=rig_namespace
    )
    rig_control_nodes = [node for node in rig_nodes if node.split('|')[-1].split(':')[-1] in actor.maya_import_mapping.keys()]

    # Import skeleton
    skeleton_nodes = _import_fbx(actor.skeleton_fbx, update=False)
    skeleton_nodes = [node for node in skeleton_nodes if node.split('|')[-1] in actor.maya_import_mapping.values()]

    # Bind controls to the skeleton
    for control, joint in actor.maya_import_mapping.items():
        if not cmds.objExists(f'{rig_namespace}:{control}'):
            _logger.warning("Control '%s' does not exist.", f'{rig_namespace}:{control}')
            continue
        if not cmds.objExists(joint):
            _logger.warning("Joint '%s' does not exist.", joint)
            continue
        cmds.parentConstraint(joint, f'{rig_namespace}:{control}', maintainOffset=True)

    # Import the animation onto the skeleton
    _import_fbx(fbx_file, update=True)

    # Bake animation on controls
    try:
        cmds.refresh(su=True)
        start = cmds.playbackOptions(minTime=True, q=True)
        end = cmds.playbackOptions(maxTime=True, q=True)
        cmds.bakeResults(rig_control_nodes, at=['tx', 'ty', 'tz', 'rx', 'ry', 'rz'], t=(start, end), simulation=True)
    finally:
        cmds.refresh(su=False)

    cmds.delete(skeleton_nodes)