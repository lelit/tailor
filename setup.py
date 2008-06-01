#!/usr/bin/env python

from os import walk
try:
        from setuptools import setup
except ImportError:
        from distutils.core import setup
from vcpx.tailor import __version__ as VERSION

setup(name='tailor',
      version=VERSION,
      author='Lele Gaifax',
      author_email='lele@nautilus.homeip.net',
      packages=[dirpath for dirpath, dirnames, filenames in walk('vcpx')
                if dirpath <> 'vcpx/tests' and '__init__.py' in filenames],
      scripts=['tailor'],
      description='A tool to migrate changesets between various kinds of '
      'version control system.',
      long_description="""\
With its ability to "translate the history" from one VCS kind to another,
this tool makes it easier to keep the upstream changes merged in
a own branch of a product.

Tailor is able to fetch the history from Arch, Bazaar, CVS, Darcs, Monotone,
Perforce or Subversion and rewrite it over Aegis, Bazaar, CVS, Darcs, Git,
Mercurial, Monotone and Subversion.
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
        ]
    )
