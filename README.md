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