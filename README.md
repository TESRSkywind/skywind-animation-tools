# Skywind

The animation pipeline for Skywind.

---

## Installation

### Maya
1. Download the entire repository as a .zip file.
2. Move the `skywind` directory to your Maya scripts directory.
3. Either move `usersetup.py` to your script directory or add the following lines to an existing one:
```
from skywind.maya import startup
startup.initialize()
```

### Blender
1. Download the entire repository as a .zip file.
2. Install `./skywind/__init__.py` as an add-on.

### Blender (Local Development)
1. Clone the repository
2. Set your system BLENDER_USER_EXTENSIONS environment variable to the repositories directory
3. In Blender, under *Edit > Preferences > Get Extensions*, click the *Repositories* dropdown and expand *Advanced*. Set *Module* to `skywind_animation_tools`  
4. Under *Edit > Preferences > Add-ons*, enable the *Skywind* add-on