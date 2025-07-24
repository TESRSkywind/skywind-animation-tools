
from logging import *

STREAM_FORMATTER = Formatter('%(name)s :: %(levelname)s :: %(message)s')

# def setup_blender_logger(name="BlenderLogger", level=DEBUG):
#     """
#     Set up a logger that outputs messages to Blender's system console.
#     """
#     logger = getLogger(name)
#
#     # Avoid adding multiple handlers if this function is called multiple times
#     if not logger.handlers:
#         logger.setLevel(level)
#
#         # Create a console handler
#         console_handler = StreamHandler()
#         console_handler.setLevel(level)
#
#         # Create formatter and add it to the handler
#         formatter = Formatter('%(levelname)s:%(name)s: %(message)s')
#         console_handler.setFormatter(formatter)
#
#         # Add the handler to the logger
#         logger.addHandler(console_handler)
#
#     return logger


def initialize():

    root_logger = getLogger()
    root_logger.propagate = False
    root_logger.setLevel(DEBUG)

    # console_handler = StreamHandler(stream=sys.stdout)
    console_handler = StreamHandler()
    console_handler.setLevel(DEBUG)
    console_handler.setFormatter(STREAM_FORMATTER)
    root_logger.addHandler(console_handler)

    logger = getLogger(__name__)
    logger.debug('initialized default logging')