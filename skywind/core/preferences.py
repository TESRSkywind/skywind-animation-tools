
import winreg
import logging


__all__ = ['get_last_dir', 'set_last_dir']
_logger = logging.getLogger(__name__)
LAST_DIRECTORY_KEY = "LastDirectory"
REG_PATH = r"Software\SkywindAnimation"


def get_last_dir() -> str:
    try:
        registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(registry_key, LAST_DIRECTORY_KEY)
        winreg.CloseKey(registry_key)
        return value
    except FileNotFoundError:
        pass
    return os.path.expanduser("~")


def set_last_dir(path: str):
    _logger.debug('Saving last directory: %s', path)
    winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH)
    registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_WRITE)
    winreg.SetValueEx(registry_key, LAST_DIRECTORY_KEY, 0, winreg.REG_SZ, path)
    winreg.CloseKey(registry_key)