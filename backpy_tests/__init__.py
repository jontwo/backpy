import logging

__author__ = 'jonmorris'
__version__ = '1.1'

logging.basicConfig(format='    %(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
