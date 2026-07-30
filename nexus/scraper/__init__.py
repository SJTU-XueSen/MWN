import sys, os
_site_packages = os.path.join(os.path.dirname(sys.executable), 'Lib', 'site-packages')
if _site_packages not in sys.path:
    sys.path.insert(0, _site_packages)
