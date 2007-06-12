# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Darcs details
# :Creato:   ven 18 giu 2004 14:45:28 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

"""
This module contains supporting classes for the ``darcs`` versioning system.
"""

__docformat__ = 'reStructuredText'

import re

from vcpx.repository import Repository
from vcpx.shwrap import ExternalCommand
from vcpx.target import TargetInitializationFailure


class DarcsRepository(Repository):
    METADIR = '_darcs'

    def _load(self, project):
        Repository._load(self, project)
        cget = project.config.get
        self.EXECUTABLE = cget(self.name, 'darcs-command', 'darcs')
        self.use_look_for_adds = cget(self.name, 'look-for-adds', 'False')
        self.replace_badchars = eval(cget(self.name, 'replace-badchars',
                                          "{"
                                          "'\xc1': '&#193;',"
                                          "'\xc9': '&#201;',"
                                          "'\xcd': '&#205;',"
                                          "'\xd3': '&#211;',"
                                          "'\xd6': '&#214;',"
                                          "'\xd5': '&#336;',"
                                          "'\xda': '&#218;',"
                                          "'\xdc': '&#220;',"
                                          "'\xdb': '&#368;',"
                                          "'\xe1': '&#225;',"
                                          "'\xe9': '&#233;',"
                                          "'\xed': '&#237;',"
                                          "'\xf3': '&#243;',"
                                          "'\xf6': '&#246;',"
                                          "'\xf5': '&#337;',"
                                          "'\xfa': '&#250;',"
                                          "'\xfc': '&#252;',"
                                          "'\xfb': '&#369;',"
                                          "'\xf1': '&#241;',"
                                          "'\xdf': '&#223;',"
                                          "'\xe5': '&#229;'"
                                          "}"))

    def command(self, *args, **kwargs):
        if args[0] == 'record' and self.use_look_for_adds:
            args = args + ('--look-for-adds',)
        return Repository.command(self, *args, **kwargs)

    def create(self):
        from vcpx.dualwd import IGNORED_METADIRS
        from os.path import join

        cmd = self.command("initialize")
        init = ExternalCommand(cwd=self.basedir, command=cmd)
        init.execute()

        if init.exit_status:
            raise TargetInitializationFailure(
                "%s returned status %s" % (str(init), init.exit_status))

        metadir = join(self.basedir, '_darcs')
        prefsdir = join(metadir, 'prefs')
        prefsname = join(prefsdir, 'prefs')
        boringname = join(prefsdir, 'boring')

        boring = open(boringname, 'rU')
        ignored = boring.read().rstrip().split('\n')
        boring.close()

        # Augment the boring file, that contains a regexp per line
        # with all known VCs metadirs to be skipped.
        ignored.extend(['(^|/)%s($|/)' % re.escape(md)
                        for md in IGNORED_METADIRS])

        # Eventually omit our own log...
        logfile = self.projectref().logfile
        if logfile.startswith(self.basedir):
            ignored.append('^%s$' %
                           re.escape(logfile[len(self.basedir)+1:]))

        # ... and state file
        sfname = self.projectref().state_file.filename
        if sfname.startswith(self.basedir):
            sfrelname = sfname[len(self.basedir)+1:]
            ignored.append('^%s$' % re.escape(sfrelname))
            ignored.append('^%s$' % re.escape(sfrelname+'.old'))
            ignored.append('^%s$' % re.escape(sfrelname+'.journal'))

        boring = open(boringname, 'w')
        boring.write('\n'.join(ignored))
        boring.write('\n')
        boring.close()
