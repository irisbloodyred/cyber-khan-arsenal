import sys
import os

path = '/home/khan-hacker/khan_toool/backend'
if path not in sys.path:
    sys.path.append(path)

from app import app as application