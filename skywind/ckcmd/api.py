import os
import tempfile
import subprocess


CKCMD = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bin', 'ck-cmd.exe')
HKXCMD = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bin', 'hkxcmd.exe')
BEHAVIOR_CONVERTER_PATH = os.path.join(os.path.dirname(__file__), 'bin', 'HavokBehaviorPostProcess.exe')


class CkCmdException(Exception):
    """"""


def run_command(command: str, directory: str = '/') -> str:
    """
    Runs a given command in a separate process. Prints the output and raises any exceptions.

    Args:
        command(str): A command string to run.
        directory(str): A directory to run the command in.
    """
    command = command.replace('\\\\', '\\')
    directory = directory.replace('\\\\', '\\')
    print (command)
    with open(os.path.join(tempfile.gettempdir(), 'ckcmd.log'), 'w') as f:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, shell=True, cwd=directory)
        out, err = process.communicate()
        print (out)
        if process.returncode != 0 or 'Exception' in str(err):
            raise CkCmdException('\n%s' % str(err))


def export_rig(skeleton_hkx: str, skeleton_nif: str, skeleton_fbx: str,
              animation_hkx: str='', mesh_nif: str='', cache_txt: str='', behavior_directory: str='') -> str:
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
    run_command(command, directory=os.path.dirname(skeleton_fbx))
    return command


def export_animation(skeleton_hkx: str, animation_hkx: str, output_directory: str) -> str:
    """
    Converts a Skyrim animation from hkx to fbx.

    Args:
        skeleton_hkx(str): A skeleton.hkx path.
        animation_hkx(str): Either an animation hkx file or directory containing animation hkx files.
        output_directory(str): The output directory.

    Returns:
        str: The executed command string.
    """
    command = '%s exportanimation "%s" "%s" --e="%s"' % (CKCMD, skeleton_hkx, animation_hkx, output_directory)
    run_command(command, directory=output_directory)
    return command


def import_animation(
        skeleton_hkx: str, animation_fbx: str, animation_hkx: str, cache_txt: str = '', behavior_directory: str = ''
):
    """Converts an animation from fbx to hkx.

    Args:
        skeleton_hkx(str): A skeleton.hkx path.
        animation_fbx(str): An animation fbx file or directory containing animation fbx files.
        animation_hkx(str): The output fbx file.
        cache_txt(str): An optional cache file to contain root motion data.
        behavior_directory(str): An optional behavior directory.

    Returns:
        str: The executed command string.
    """
    command = f'{CKCMD} importanimation "{skeleton_hkx}" "{animation_fbx}" --c="{cache_txt}" --b="{behavior_directory}" --e="{animation_hkx}"'
    run_command(command, directory=os.path.dirname(animation_hkx))
    if not os.path.exists(animation_fbx):
        raise FileNotFoundError(f'Failed to import {animation_fbx}')
    return command