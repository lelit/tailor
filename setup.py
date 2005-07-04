#!/usr/bin/env python

from distutils.core import setup
from vcpx.tailor import __version__ as VERSION

setup(name='tailor',
    version=VERSION,
    author='Lele Gaifax',
    author_email='lele@nautilus.homeip.net',
    packages=['vcpx'],
    scripts=['tailor'],
    description='A tool to migrate changesets between CVS, Subversion, '
      'Darcs, Bazaar-ng, Codeville, Monotone and Mercurial repositories.',
    long_description="""\
This script makes it easier to keep the upstream changes merged in
a branch of a product, storing needed information such as the upstream
URI and revision in special properties on the branched directory.
""",
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Operating System :: Unix',
        'Topic :: Software Development :: Version Control',
        'License :: GNU General Public License',
        # Don't know the stability. Took a guess
        ]
    )
