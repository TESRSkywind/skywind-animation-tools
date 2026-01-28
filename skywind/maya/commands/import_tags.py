
import os
import shutil
import logging

from maya import cmds, mel
import maya.api.OpenMaya as om2

_logger = logging.getLogger(__name__)


EXPORT_JOINT_NAME = 'NPC_s_Root_s__ob_Root_cb_'


def import_fbx(filepath: str, update: bool = False, take: str = None, fill_timeline: bool = True):
    _logger.info('Importing %s', filepath)
    if not str(filepath).lower().endswith('.fbx'):
        raise RuntimeError('"%s" is not an fbx file.' % filepath)
    if not os.path.exists(filepath):
        raise RuntimeError('Path "%s" does not exist' % filepath)

    mObjects = []

    def add_node(obj, *args):
        """ A function that stores all added nodes. """
        if obj.isNull():
            return
        mObjectHandle = om2.MObjectHandle(obj)
        if not mObjectHandle.isAlive():
            return
        if not mObjectHandle.isValid():
            return
        mObjects.append((mObjectHandle, obj))

    # Create a callback to listen for new nodes.
    callback = om2.MDGMessage.addNodeAddedCallback(add_node, 'dependNode')
    try:
        # Import the file
        cmds.unloadPlugin('fbxmaya')
        cmds.loadPlugin('fbxmaya')
        mel.eval('FBXImportMode -v %s' % ('exmerge' if update else 'add'))
        mel.eval(f'FBXImportFillTimeline -v {"true" if fill_timeline else "false"}')
        if take is not None:
            mel.eval('FBXImport -f "%s" -t %s' % (filepath.replace('\\', '/'), take))
        else:
            mel.eval('FBXImport -f "%s"' % filepath.replace('\\', '/'))
    finally:
        # Always remove the callback
        om2.MMessage.removeCallback(callback)

    # Convert mObjects to node names
    nodes = set()
    for handle, obj in mObjects:
        if obj.isNull():
            continue
        if not handle.isAlive():
            continue
        if not handle.isValid():
            continue
        if obj.hasFn(om2.MFn.kDagNode):
            name = om2.MFnDagNode(obj).fullPathName()
        else:
            name = om2.MFnDependencyNode(obj).name()
        if cmds.objExists(name):
            nodes.add(name)

    return list(nodes)


def copy_tag_attributes(src_root: str, dst_root: str):
    _logger.info('Copying attributes from %s to %s', src_root, dst_root)
    for src_attr_name in cmds.listAttr(src_root, userDefined=True):
        if not cmds.attributeQuery(src_attr_name, node=dst_root, exists=True):
            sel = om2.MSelectionList()
            sel.add('%s.%s' % (src_root, src_attr_name))
            cmd = om2.MFnAttribute(sel.getPlug(0).attribute()).getAddAttrCmd(True)
            cmd = cmd.replace(';', ' %s;' % dst_root)
            mel.eval(cmd)

        cmds.copyAttr(src_root, dst_root, at=[src_attr_name], v=True)

        # Copy Animation
        if cmds.keyframe(src_root, at=[src_attr_name], q=True):
            cmds.copyKey(src_root, at=[src_attr_name])
            cmds.pasteKey(dst_root, at=[src_attr_name])



def find_root_joint(nodes: list[str] = None) -> str | None:

    if nodes is None:
        # If an exact match exists, return that
        if cmds.objExists(EXPORT_JOINT_NAME):
            return cmds.ls(EXPORT_JOINT_NAME, long=True)[0]

        # Otherwise search for another match
        export_joints = cmds.ls('*:%s' % EXPORT_JOINT_NAME, type='joint') or []
        if len(export_joints) == 1:
            return export_joints[0]
        return None

    else:
        # Otherwise search the nodes for the joint
        for node in nodes:
            if node.split('|')[-1].split(':')[-1] == EXPORT_JOINT_NAME:
                return node
        return None


def import_animation_tags(fbx_file: str = None, joint: str = None):
    _logger.info('Importing animation tags')

    if not fbx_file:
        result = cmds.fileDialog2(
            fileMode=1,
            caption="Select FBX file",
            fileFilter="FBX Files (*.fbx)"
        )
        if not result:
            _logger.warning("No FBX file selected.")
            return
        fbx_file = result[0]

    if joint is None:
        joint = find_root_joint()

    imported_nodes = import_fbx(fbx_file, fill_timeline=False)
    try:
        root_joint = None
        for imported_joint in cmds.ls(imported_nodes, type='joint', long=True):
            if cmds.listRelatives(imported_joint, parent=True) is None:
                root_joint = imported_joint
        if root_joint is None:
            raise RuntimeError('Failed to find root joint in %s' % fbx_file)
        _logger.info('Copying tags from %s to %s', root_joint, joint)
        copy_tag_attributes(root_joint, joint)
    finally:
        cmds.delete(imported_nodes)


def export_fbx(nodes: list[str], path: str):
    _logger.info('Exporting %s nodes to %s', len(nodes), path)
    # Determine what nodes we're exporting
    nodes = [node for node in nodes if 'shape' not in cmds.nodeType(node, i=True)]

    try:
        cmds.undoInfo(openChunk=True)

        # Ensure joints are set to export as joints
        for node in nodes:
            if cmds.nodeType(node) == 'joint' and node.endswith('_rb'):
                if cmds.attributeQuery('filmboxTypeID', node=node, exists=True):
                    cmds.setAttr('%s.filmboxTypeID' % node, 2)

        # Ensure the destination directory exists
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))

        # Export and restore the original selection
        cmds.select(nodes)
        command = 'FBXExport -f "%s" -s' % path.replace('\\', '/')
        try:
            mel.eval(command)
        except RuntimeError:
            raise RuntimeError('Error occurred during mel script: %s' % command)

    finally:
        cmds.undoInfo(closeChunk=True)
        cmds.undo()
    return path


if __name__ == '__main__':

    from maya import standalone
    standalone.initialize()

    directory = r'C:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition\Data\resources\animation\guar\animations'
    files = [
        r'turnloopingr.fbx',
        r'turncannedl90.fbx',
        r'turnloopingfastr.fbx',
        r'turnloopingfastl.fbx',
        r'turncannedr180.fbx',
        r'turncannedl180.fbx',
        r'turncannedr90.fbx',
        r'getupright.fbx',
        r'getupleft.fbx',
    ]
    tag_directory = r'E:\Projects\Skywind\Projects\guar\project\import\tags'
    for filename in files:
        filepath = os.path.join(directory, filename)
        tag_file = os.path.join(tag_directory, filename)

        cmds.file(newFile=True, force=True)
        nodes = import_fbx(filepath)
        import_animation_tags(tag_file, find_root_joint(nodes))
        shutil.copyfile(filepath, os.path.join(directory, filename.replace('.fbx', '.fbx1')))
        export_fbx(nodes, filepath)
