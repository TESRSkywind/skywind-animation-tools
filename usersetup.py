""" Maya startup functionality. """

from maya import cmds
cmds.evalDeferred('from skywind.maya import startup;startup.initialize()')