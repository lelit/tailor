# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Tests for svndump source backend
# :Creato:   gio 01 set 2005 10:47:17 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
# 

from unittest import TestCase, TestSuite
from datetime import datetime
from StringIO import StringIO
from vcpx.svndump import changesets_from_svndump

class SvndumpParserTest(TestCase):
    """Ensure the svndump parser does its job."""

    SIMPLE_TEST = r"""SVN-fs-dump-format-version: 2

UUID: c285bdbe-b1ff-0310-9ce6-89454991beb6

Revision-number: 0
Prop-content-length: 56
Content-length: 56

K 8
svn:date
V 27
2005-09-01T08:36:44.518389Z
PROPS-END

Revision-number: 1
Prop-content-length: 113
Content-length: 113

K 7
svn:log
V 14
Initial import
K 10
svn:author
V 4
lele
K 8
svn:date
V 27
2005-09-01T08:38:41.788715Z
PROPS-END

Node-path: bash.bashrc
Node-kind: file
Node-action: add
Prop-content-length: 10
Text-content-length: 980
Text-content-md5: 56132976d5243ea699c3f974ee886b88
Content-length: 990

PROPS-END
1# System-wide .bashrc file for interactive bash(1) shells.

# To enable the settings / commands in this file for login shells as well,
# this file has to be sourced in /etc/profile.

# If not running interactively, don't do anything
[ -z "$PS1" ] && return

# check the window size after each command and, if necessary,
# update the values of LINES and COLUMNS.
shopt -s checkwinsize

# set variable identifying the chroot you work in (used in the prompt below)
if [ -z "$debian_chroot" -a -r /etc/debian_chroot ]; then
    debian_chroot=$(cat /etc/debian_chroot)
fi

# set a fancy prompt (non-color, overwrite the one in /etc/profile)
PS1='${debian_chroot:+($debian_chroot)}\u@\h:\w\$ '

# If this is an xterm set the title to user@host:dir
case "$TERM" in
xterm*|rxvt*)
    PROMPT_COMMAND='echo -ne "\033]0;${USER}@${HOSTNAME}: ${PWD}\007"'
    ;;
*)
    ;;
esac

# enable bash completion in interactive shells
if [ -f /etc/bash_completion ]; then
    . /etc/bash_completion
fi


Revision-number: 2
Prop-content-length: 114
Content-length: 114

K 7
svn:log
V 15
Rename the file
K 10
svn:author
V 4
lele
K 8
svn:date
V 27
2005-09-01T08:39:34.777407Z
PROPS-END

Node-path: bashrc
Node-kind: file
Node-action: add
Node-copyfrom-rev: 1
Node-copyfrom-path: bash.bashrc


Node-path: bash.bashrc
Node-action: delete


Revision-number: 3
Prop-content-length: 109
Content-length: 109

K 7
svn:log
V 10
Add subdir
K 10
svn:author
V 4
lele
K 8
svn:date
V 27
2005-09-01T08:42:42.256576Z
PROPS-END

Node-path: subdir
Node-kind: dir
Node-action: add
Prop-content-length: 10
Content-length: 10

PROPS-END


Node-path: subdir/other.version
Node-kind: file
Node-action: add
Node-copyfrom-rev: 2
Node-copyfrom-path: bashrc


Revision-number: 4
Prop-content-length: 112
Content-length: 112

K 7
svn:log
V 13
Rename subdir
K 10
svn:author
V 4
lele
K 8
svn:date
V 27
2005-09-01T08:43:11.241298Z
PROPS-END

Node-path: somethingelse
Node-kind: dir
Node-action: add
Node-copyfrom-rev: 3
Node-copyfrom-path: subdir


Node-path: subdir
Node-action: delete


Revision-number: 5
Prop-content-length: 114
Content-length: 114

K 7
svn:log
V 15
Rename and edit
K 10
svn:author
V 4
lele
K 8
svn:date
V 27
2005-09-01T08:44:11.867933Z
PROPS-END

Node-path: bash.profile
Node-kind: file
Node-action: add
Node-copyfrom-rev: 2
Node-copyfrom-path: bashrc
Text-content-length: 60
Text-content-md5: b91bd7d6d6fbd61901f9588511b49ec4
Content-length: 60

# System-wide .bashrc file for interactive bash(1) shells.



Node-path: bashrc
Node-action: delete


"""

    def testBasicBehaviour(self):
        "Verify basic svndump parser behaviour"

        log = StringIO(self.SIMPLE_TEST)
        csets = changesets_from_svndump(log)

        self.assertEqual(len(csets), 5)

        cset = csets[0]
        self.assertEqual(cset.author, "lele")
        self.assertEqual(cset.date, datetime(2005, 9, 1, 8, 38, 41, 788715))
        self.assertEqual(cset.log, "Initial import")

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'bash.bashrc')
        self.assertEqual(entry.action_kind, entry.ADDED)
        self.assertEqual(entry.text_length, 980)

        cset = csets[1]
        self.assertEqual(cset.log, "Rename the file")

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'bashrc')
        self.assertEqual(entry.old_name, 'bash.bashrc')
        self.assertEqual(entry.action_kind, entry.RENAMED)
        self.assertEqual(entry.text_length, None)

        cset = csets[2]
        self.assertEqual(cset.log, "Add subdir")

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'subdir')
        self.assertEqual(entry.action_kind, entry.ADDED)
        self.assertEqual(entry.text_length, None)
