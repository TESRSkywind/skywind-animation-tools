import os.path
import site
from . import log


SKYWIND_DIRECTORY = os.path.dirname(os.path.dirname(__file__))
SITE_DIRECTORIES = (
        os.path.join(SKYWIND_DIRECTORY, 'site-packages', '3.11'),
        os.path.join(SKYWIND_DIRECTORY, 'site-packages', 'any')
)

def initialize():
    log.initialize()
    for path in SITE_DIRECTORIES:
        site.addsitedir(path)
