import os
import tempfile
import subprocess
from contextlib import contextmanager


CKCMD = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bin', 'ck-cmd.exe')
HKXCMD = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bin', 'hkxcmd.exe')
HKXCONV = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bin', 'hkxconv.exe')
BEHAVIOR_CONVERTER_PATH = os.path.join(os.path.dirname(__file__), 'bin', 'HavokBehaviorPostProcess.exe')


class CkCmdException(Exception):
    """"""


@contextmanager
def ensure_file_modified(filepath: str):
    existed = os.path.exists(filepath)
    mtime = None if not existed else os.path.getmtime(filepath)
    yield
    if not os.path.exists(filepath):
        raise FileNotFoundError(f'{filepath} does not exist')
    if mtime and mtime == os.path.getmtime(filepath):
        raise FileExistsError(f'{filepath} was not modified')


def _run_command(command: str, directory: str = '/'):
    """
    Runs a given command in a separate process. Prints the output and raises any exceptions.

    Args:
        command(str): A command string to run.
        directory(str): A directory to run the command in.
    """
    command = command.replace('\\\\', '\\')
    directory = directory.replace('\\\\', '\\')
    print (command)
    with open(os.path.join(tempfile.gettempdir(), 'ck.log'), 'w') as f:
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True, shell=True, cwd=directory)
        except Exception as e:
            raise CkCmdException('Command "%s" failed.' % command) from e
        out, err = process.communicate()
        print (out)
        if process.returncode != 0 or 'Exception' in str(err):
            raise CkCmdException('\n%s' % str(err))


def convert_hkx_to_xml(hkx: str, xml: str = None) -> str:
    """Converts an HKX file to XML"""
    if xml is None:
        xml = os.path.join(tempfile.gettempdir(), os.path.basename(hkx).split('.')[0] + '.xml')
    with ensure_file_modified(xml):
        command = f'{HKXCONV} convert "{hkx}" "{xml}"'
        _run_command(command)
    return xml


def convert_xml_to_le_hkx(xml: str, le_hkx: str = None) -> str:
    """Converts an XML file to a legacy HKX file"""
    if le_hkx is None:
        le_hkx = os.path.join(tempfile.gettempdir(), os.path.basename(xml).split('.')[0] + '_le.hkx')
    with ensure_file_modified(le_hkx):
        output_directory = os.path.dirname(le_hkx)
        command = f'"{CKCMD}" convert "{xml}" -o "{le_hkx}" -v WIN32 -f SAVE_DEFAULT'
        _run_command(command, directory=output_directory)
    return xml


def export_rig(skeleton_hkx: str, skeleton_nif: str, skeleton_fbx: str,
              animation_hkx: str='', mesh_nif: str='', cache_txt: str='', behavior_directory: str=''):
    """Converts a Skyrim rig from hkx to fbx."""
    commands = [CKCMD, "exportrig"]
    commands.append('"%s"' % skeleton_hkx)
    commands.append('"%s"' % skeleton_nif)
    commands.append('--e="%s"' % skeleton_fbx)
    if animation_hkx:
        commands.append('--a="%s"' % animation_hkx)
    if mesh_nif:
        commands.append('--n="%s"' % mesh_nif)
    if behavior_directory:
        commands.append('--b="%s"' % behavior_directory)
    if cache_txt:
        commands.append('--c="%s"' % cache_txt)
    command = ' '.join(commands)
    _run_command(command, directory=os.path.dirname(skeleton_fbx))


def convert_animation_hkx_to_fbx(skeleton_hkx: str, animation_hkx: str, output_directory: str):
    """
    Converts a Skyrim animation from hkx to fbx.

    Args:
        skeleton_hkx(str): A skeleton.hkx path.
        animation_hkx(str): Either an animation hkx file or directory containing animation hkx files.
        output_directory(str): The output directory.
    """
    skeleton_le_hkx = convert_xml_to_le_hkx(convert_hkx_to_xml(skeleton_hkx))
    animation_le_hkx = convert_xml_to_le_hkx(convert_hkx_to_xml(animation_hkx))
    command = '%s exportanimation "%s" "%s" --e="%s"' % (CKCMD, skeleton_le_hkx, animation_le_hkx, output_directory)
    _run_command(command, directory=output_directory)


def convert_animation_fbx_to_hkx(
        skeleton_hkx: str, animation_fbx: str, output_directory: str, cache_txt: str = '', behavior_directory: str = ''
):
    """Converts an animation from fbx to hkx.

    Args:
        skeleton_hkx(str): A skeleton.hkx path.
        animation_fbx(str): An animation fbx file or directory containing animation fbx files.
        output_directory(str): The output directory.
        cache_txt(str): An optional cache file to contain root motion data.
        behavior_directory(str): An optional behavior directory.
    """
    command = f'{CKCMD} importanimation "{skeleton_hkx}" "{animation_fbx}" --c="{cache_txt}" --b="{behavior_directory}" --e="{output_directory}"'
    _run_command(command, directory=output_directory)
    output_file = os.path.join(output_directory, os.path.basename(animation_fbx).replace('.fbx', '.hkx'))
    if not os.path.exists(output_file):
        raise FileNotFoundError(f'Failed to import {animation_fbx}')


if __name__ == '__main__':
    convert_animation_hkx_to_fbx(
        r'C:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition\Data\meshes\actors\character\character assets\skeleton.hkx',
        r'C:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition\Data\meshes\actors\character\animations\OpenAnimationReplacer\Skywind\1_Spears\2hw_attackright.hkx',
        r'C:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition\Data\meshes\actors\character\animations\OpenAnimationReplacer\Skywind\1_Spears'
    )