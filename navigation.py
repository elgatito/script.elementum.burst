import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'resources', 'site-packages'))

from burst import navigation

navigation.run()
