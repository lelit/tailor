# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Darcs specific tests
# :Creato:   sab 17 lug 2004 02:33:41 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

from unittest import TestCase
from datetime import datetime
from StringIO import StringIO
from vcpx.repository.darcs.source import changesets_from_darcschanges
from vcpx.shwrap import ExternalCommand, PIPE
from vcpx.tzinfo import UTC


class DarcsChangesParser(TestCase):
    """Tests for the parser of darcs changes"""

    SIMPLE_TEST = """\
<changelog>
<patch author='lele@nautilus.homeip.net' date='20040716123737' local_date='Fri Jul 16 14:37:37 CEST 2004' inverted='False' hash='20040716123737-97f81-9db0d923d2ba6f4c3808cb04a4ae4cf99fed185b.gz'>
        <name>Fix the CVS parser to omit already seen changesets</name>
        <comment>For some unknown reasons....</comment>

    <summary>
    <modify_file>vcpx/cvs.py<removed_lines num='4'/><added_lines num='11'/></modify_file>
    <modify_file>vcpx/tests/cvs.py<removed_lines num='14'/><added_lines num='32'/></modify_file>
    </summary>

</patch>

<patch author='lele@nautilus.homeip.net' date='20040601140559' local_date='Tue Jun  1 16:05:59 CEST 2004' inverted='False' hash='20040601140559-97f81-b669594864cb35290fbe4848e6645e73057a8caf.gz'>
        <name>Svn log parser with test</name>

    <summary>
    <modify_file>cvsync/svn.py<removed_lines num='1'/><added_lines num='93'/></modify_file>
    <modify_file>cvsync/tests/__init__.py<added_lines num='1'/></modify_file>
    <add_file>cvsync/tests/svn.py</add_file>
    <add_file>cvsync/tests/testrepo.dump</add_file>
    </summary>

</patch>

</changelog>
"""

    def testBasicBehaviour(self):
        """Verify basic darcs changes parser behaviour"""

        log = StringIO(self.SIMPLE_TEST)

        csets = changesets_from_darcschanges(log)

        cset = csets.next()
        self.assertEqual(cset.revision,
                         "Fix the CVS parser to omit already seen changesets")
        self.assertEqual(cset.author, "lele@nautilus.homeip.net")
        self.assertEqual(cset.date, datetime(2004, 7, 16, 12, 37, 37, 0, UTC))
        self.assertEqual(cset.log, "For some unknown reasons....")
        entry = cset.entries[0]
        self.assertEqual(entry.name, 'vcpx/cvs.py')
        self.assertEqual(entry.action_kind, entry.UPDATED)

        cset = csets.next()
        self.assertEqual(cset.revision,
                         "Svn log parser with test")
        self.assertEqual(cset.date, datetime(2004, 6, 1, 14, 5, 59, 0, UTC))
        self.assertEqual(len(cset.entries), 4)
        self.assertEqual(cset.darcs_hash,
                         '20040601140559-97f81-b669594864cb35290fbe4848e6645e73057a8caf.gz')

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'cvsync/svn.py')
        self.assertEqual(entry.action_kind, entry.UPDATED)
        entry = cset.entries[1]
        self.assertEqual(entry.name, 'cvsync/tests/__init__.py')
        self.assertEqual(entry.action_kind, entry.UPDATED)
        entry = cset.entries[2]
        self.assertEqual(entry.name, 'cvsync/tests/svn.py')
        self.assertEqual(entry.action_kind, entry.ADDED)
        entry = cset.entries[3]
        self.assertEqual(entry.name, 'cvsync/tests/testrepo.dump')
        self.assertEqual(entry.action_kind, entry.ADDED)

    def testOnTailorOwnRepo(self):
        """Verify fetching unidiff of a darcs patch"""

        from os import getcwd

        patchname = 'more detailed diags on SAXException'
        changes = ExternalCommand(command=["darcs", "changes", "--xml", "--summary",
                                           "--patches", patchname])
        csets = changesets_from_darcschanges(changes.execute(stdout=PIPE)[0],
                                             unidiff=True,
                                             repodir=getcwd())
        unidiff = csets.next().unidiff
        head = unidiff.split('\n')[0]
        self.assertEqual(head, 'Thu Jun  9 22:17:11 CEST 2005  zooko@zooko.com')

    ALL_ACTIONS_TEST = """\
<changelog>
<patch author='' date='20050811140203' local_date='Thu Aug 11 16:02:03 CEST 2005' inverted='False' hash='20050811140203-da39a-0a36c886b2479b20ab9188781fe2e51f9a50a175.gz'>
        <name>first</name>
    <summary>
    <add_file>
    a.txt
    </add_file>
    <add_directory>
    dir
    </add_directory>
    </summary>
</patch>
<patch author='' date='20050811140254' local_date='Thu Aug 11 16:02:54 CEST 2005' inverted='False' hash='20050811140254-da39a-b2ad279f1d7edae8e07b7b1ea8f3e63dbb242bf0.gz'>
        <name>removed</name>
    <summary>
    <remove_directory>
    dir
    </remove_directory>
    </summary>
</patch>
<patch author='' date='20050811140314' local_date='Thu Aug 11 16:03:14 CEST 2005' inverted='False' hash='20050811140314-da39a-de701bff466827b91e51658e411c768f43abc1b0.gz'>
        <name>moved</name>
    <summary>
    <move from="bdir" to="dir"/>
    <add_directory>
    bdir
    </add_directory>
    </summary>
</patch>
<patch author='lele@metapensiero.it' date='20050811143245' local_date='Thu Aug 11 16:32:45 CEST 2005' inverted='False' hash='20050811143245-7a6fb-663bb3085e9b7996f554e4bd9d2f0b13208d65e0.gz'>
        <name>modified</name>
    <summary>
    <modify_file>
    a.txt<added_lines num='3'/>
    </modify_file>
    </summary>
</patch>
</changelog>
"""

    def testAllActions(self):
        """Verify darcs changes parser understand all actions"""

        log = StringIO(self.ALL_ACTIONS_TEST)

        csets = list(changesets_from_darcschanges(log))

        self.assertEqual(len(csets), 4)

        cset = csets[0]
        self.assertEqual(cset.revision, 'first')
        self.assertEqual(len(cset.entries), 2)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'a.txt')
        self.assertEqual(entry.action_kind, entry.ADDED)
        entry = cset.entries[1]
        self.assertEqual(entry.name, 'dir')
        self.assertEqual(entry.action_kind, entry.ADDED)

        cset = csets[1]
        self.assertEqual(cset.revision, 'removed')
        self.assertEqual(len(cset.entries), 1)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'dir')
        self.assertEqual(entry.action_kind, entry.DELETED)

        cset = csets[2]
        self.assertEqual(cset.revision, 'moved')
        self.assertEqual(len(cset.entries), 1)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'dir')
        self.assertEqual(entry.action_kind, entry.ADDED)

        cset = csets[3]
        self.assertEqual(cset.revision, 'modified')
        self.assertEqual(len(cset.entries), 1)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'a.txt')
        self.assertEqual(entry.action_kind, entry.UPDATED)

    def testIncrementalParser(self):
        """Verify that the parser is effectively incremental"""

        log = StringIO(self.ALL_ACTIONS_TEST)

        csets = list(changesets_from_darcschanges(log, chunksize=100))
        self.assertEqual(len(csets), 4)

    OLD_DATE_FORMAT_TEST = """\
<changelog>
<patch author='David Roundy &lt;droundy@abridgegame.org&gt;' date='Tue Oct 14 09:42:00 EDT 2003' local_date='Tue Oct 14 15:42:00 CEST 2003' inverted='False' hash='20031014094200-53a90-5896ac929692179d06a42af70f273800e4842603.gz'>
        <name>use new select code in record.</name>
</patch>
<patch author='David Roundy &lt;droundy@abridgegame.org&gt;' date='20031014140231' local_date='Tue Oct 14 16:02:31 CEST 2003' inverted='False' hash='20031014140231-53a90-f5b6f441d32bd49d8ceacd6d804f31a462f94b88.gz'>
        <name>use iso format for dates in record.</name>
</patch>
</changelog>
"""

    def testOldDateFormat(self):
        """Verify that the parser understands date format used by old darcs"""

        log = StringIO(self.OLD_DATE_FORMAT_TEST)

        csets = changesets_from_darcschanges(log)

        cset = csets.next()
        self.assertEqual(cset.date, datetime(2003, 10, 14, 9, 42, 0, 0, UTC))

        cset = csets.next()
        self.assertEqual(cset.date, datetime(2003, 10, 14, 14, 2, 31, 0, UTC))

    RENAME_THEN_REMOVE_TEST = """
<changelog>
<patch author='lele@nautilus.homeip.net' date='20060525213905' local_date='Thu May 25 23:39:05 CEST 2006' inverted='False' hash='20060525213905-97f81-292b84413dfdfca140fe104eb29273b50cb5701a.gz'>
        <name>Move A to B and delete B</name>
    <summary>
    <move from="fileA" to="fileB"/>
    <remove_file>
    fileB
    </remove_file>
    </summary>
</patch>
</changelog>
"""

    def testRenameAndRemove(self):
        """Verify that the parser degrades rename A B+remove B  to remove A"""

        log = StringIO(self.RENAME_THEN_REMOVE_TEST)
        csets = changesets_from_darcschanges(log)

        cset = csets.next()
        self.assertEqual(len(cset.entries), 1)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'fileA')
        self.assertEqual(entry.action_kind, entry.DELETED)

    BAD_XML_ORDER_TEST = """
<changelog>
<patch author='robert.mcqueen@collabora.co.uk' date='20060121232733' local_date='Sun Jan 22 00:27:33 CET 2006' inverted='False' hash='20060121232733-0e791-01925e82713877d33452566a27eaad4184e287df.gz'>
        <name>remove any possibility for darcs crack when moving from generated XML or generated source to the live tree, by putting the generated code in the live tree, and make whoever is doing the generation pull the changes over manually</name>
    <summary>
    <move from="tools/Makefile.am" to="generate/Makefile.am"/>
    <move from="tools/generrors.py" to="generate/generrors.py"/>
    <move from="tools/gengobject.py" to="generate/gengobject.py"/>
    <move from="gabble-connection-manager.xml" to="generate/xml-modified/gabble-connection-manager.xml"/>
    <move from="gabble-connection.xml" to="generate/xml-modified/gabble-connection.xml"/>
    <move from="gabble-im-channel.xml" to="generate/xml-modified/gabble-im-channel.xml"/>
    <move from="tools/README-do_gen" to="generate/README"/>
    <move from="tools/do_gen.sh" to="generate/do_src.sh"/>
    <move from="generate/added.sh" to="generate/added-then-renamed.sh"/>
    <modify_file>
    Makefile.am<removed_lines num='1'/><added_lines num='1'/>
    </modify_file>
    <add_directory>
    generate
    </add_directory>
    <modify_file>
    generate/README<removed_lines num='2'/><added_lines num='14'/>
    </modify_file>
    <modify_file>
    generate/do_src.sh<removed_lines num='8'/><added_lines num='19'/>
    </modify_file>
    <add_file>
    generate/do_xml.sh
    </add_file>
    <add_file>
    generate/gabble.def
    </add_file>
    <remove_file>
    generate/generrors.py
    </remove_file>
    <remove_file>
    generate/gengobject.py
    </remove_file>
    <add_directory>
    generate/src
    </add_directory>
    <add_file>
    generate/src/gabble-connection-manager-signals-marshal.list
    </add_file>
    <add_file>
    generate/src/gabble-connection-manager.c
    </add_file>
    <add_file>
    generate/src/gabble-connection-manager.h
    </add_file>
    <add_file>
    generate/src/gabble-connection-signals-marshal.list
    </add_file>
    <add_file>
    generate/src/gabble-connection.c
    </add_file>
    <add_file>
    generate/src/gabble-connection.h
    </add_file>
    <add_file>
    generate/src/gabble-im-channel-signals-marshal.list
    </add_file>
    <add_file>
    generate/src/gabble-im-channel.c
    </add_file>
    <add_file>
    generate/src/gabble-im-channel.h
    </add_file>
    <add_file>
    generate/src/telepathy-errors.h
    </add_file>
    <add_directory>
    generate/xml-modified
    </add_directory>
    <add_directory>
    generate/xml-pristine
    </add_directory>
    <add_file>
    generate/xml-pristine/gabble-connection-manager.xml
    </add_file>
    <add_file>
    generate/xml-pristine/gabble-connection.xml
    </add_file>
    <add_file>
    generate/xml-pristine/gabble-im-channel.xml
    </add_file>
    <remove_directory>
    tools
    </remove_directory>
    <add_file>
    generate/added.sh
    </add_file>
    </summary>
</patch>
</changelog>
"""

    def testBadOrderedXML(self):
        "Verify if the parser is able to correct the bad order produced by changes --xml"

        log = StringIO(self.BAD_XML_ORDER_TEST)
        csets = changesets_from_darcschanges(log)

        cset = csets.next()

        # Verify that each renamed entry is not within a directory added or renamed
        # by a following hunk
        for i,e in enumerate(cset.entries):
            if e.action_kind == e.RENAMED:
                postadds = [n.name for n in cset.entries[i+1:]
                            if ((e.name.startswith(n.name+'/') or (e.old_name==n.name)) and
                                (n.action_kind==n.ADDED or n.action_kind==n.RENAMED))]
                self.assertEqual(postadds, [])

    ADD_THEN_RENAME_TEST = """
<changelog>
<patch author='ydirson@altern.org' date='20060702232916' local_date='Mon Jul  3 01:29:16 CEST 2006' inverted='False' hash='20060702232916-130f5-728038e54e0a59bb3567d8aa170610c2eaf370ff.gz'>
        <name>[git] split git.py into source+target modules</name>
        <comment>
This allows to get more accurate coverage stats.  Eg. my test tree now
exercises the git backend like:

Name                                  Stmts   Exec  Cover
---------------------------------------------------------
vcpx/repository/git/__init__             44     37    84%
vcpx/repository/git/source               95      0     0%
vcpx/repository/git/target              154    115    74%
vcpx/target                             249    173    69%</comment>
    <summary>
    <move from="vcpx/repository/git.py" to="vcpx/repository/git/target.py"/>
    <move from="vcpx/repository/git/core.py" to="vcpx/repository/git/__init__.py"/>
    <add_directory>
    vcpx/repository/git
    </add_directory>
    <modify_file>
    vcpx/repository/git/__init__.py<added_lines num='81'/>
    </modify_file>
    <add_file>
    vcpx/repository/git/core.py
    </add_file>
    <add_file>
    vcpx/repository/git/source.py
    </add_file>
    <modify_file conflict='true'>
    vcpx/repository/git/target.py<removed_lines num='12'/><added_lines num='7'/>    </modify_file>
    </summary>
</patch>
</changelog>
"""

    MIXED_TEST = """
<changelog>
<patch author='esj@harvee.org' date='20050104213401' local_date='Tue Jan  4 22:34:01 CET 2005' inverted='False' hash='20050104213401-fab45-49c3d772521e523fa84be43883b235dbcbf9d61c.gz'>
        <name>feedback and logging </name>
        <comment>this patch has three major changes.  First is the addition of the
false negative feedback so that spam that leaks through
can be identified and corrected.

second is the logging changes minimizing information
dumped at the highest levels (1) in order to speed up message processing

third is updating portalocker for modern pythons.
</comment>
    <summary>
    <move from="ancillary/mbox2rpc.py" to="ancillary/fnsource.py"/>
    <move from="ancillary/rpc2mbox.py" to="web-ui/cgi-exec/fnsink.py"/>
    <modify_file>
    ancillary/fnsource.py<added_lines num='335'/>
    </modify_file>
    <modify_file>
    ancillary/global_configuration<added_lines num='8'/>
    </modify_file>
    <add_file>
    ancillary/mbox2rpc.py
    </add_file>
    <modify_file>
    ancillary/mbox2spamtrap.py<removed_lines num='1'/><added_lines num='1'/>
    </modify_file>
    <add_file>
    ancillary/rpc2mbox.py
    </add_file>
    <modify_file>
    modules/camram_email.py<removed_lines num='17'/><added_lines num='33'/>
    </modify_file>
    <modify_file>
    modules/camram_utils.py<removed_lines num='2'/><added_lines num='5'/>
    </modify_file>
    <modify_file>
    modules/configuration.py<removed_lines num='15'/><added_lines num='15'/>
    </modify_file>
    <modify_file>
    modules/dbm_utils.py<removed_lines num='4'/><added_lines num='4'/>
    </modify_file>
    <modify_file>
    modules/log.py<removed_lines num='1'/><added_lines num='1'/>
    </modify_file>
    <modify_file>
    modules/portalocker.py<removed_lines num='2'/><added_lines num='2'/>
    </modify_file>
    <modify_file>
    sgid/build.sh<removed_lines num='1'/><added_lines num='4'/>
    </modify_file>
    <modify_file>
    src/core_filter.py<removed_lines num='50'/><added_lines num='55'/>
    </modify_file>
    <modify_file>
    src/postfix_filter.py<removed_lines num='35'/><added_lines num='49'/>
    </modify_file>
    <modify_file>
    src/postfix_stamper.py<removed_lines num='17'/><added_lines num='18'/>
    </modify_file>
    <modify_file>
    web-ui/cgi-exec/correct.py<removed_lines num='17'/><added_lines num='17'/>
    </modify_file>
    <modify_file>
    web-ui/cgi-exec/edit_config.py<removed_lines num='23'/><added_lines num='26'/>
    </modify_file>
    <modify_file>
    web-ui/cgi-exec/fnsink.py<added_lines num='154'/>
    </modify_file>
    <modify_file>
    web-ui/cgi-exec/recover.py<removed_lines num='5'/><added_lines num='5'/>
    </modify_file>
    <modify_file>
    web-ui/cgi-exec/spamtrap_display.py<removed_lines num='4'/><added_lines num='4'/>
    </modify_file>
    <modify_file>
    web-ui/templates/correct.html<removed_lines num='1'/><added_lines num='1'/>
    </modify_file>
    </summary>
</patch>
</changelog>
"""

    def testAddAndRename(self):
        "Verify if the parser degrades (add A)+(rename A B) to (add B)"

        log = StringIO(self.ADD_THEN_RENAME_TEST)
        csets = changesets_from_darcschanges(log)

        cset = csets.next()

        entry = cset.entries[2]
        self.assertEqual(entry.name, 'vcpx/repository/git/__init__.py')
        self.assertEqual(entry.action_kind, entry.ADDED)

        log = StringIO(self.MIXED_TEST)
        csets = changesets_from_darcschanges(log)

        cset = csets.next()
        self.assertEqual([], [e for e in cset.entries if e.name == 'ancillary/mbox2rpc.py'])
        self.assertEqual([], [e for e in cset.entries if e.action_kind == e.RENAMED])

    ADD_THEN_REMOVE_TEST = """
<changelog>
<patch author='Erik Schnetter &lt;schnetter@aei.mpg.de&gt;' date='20050606193150' local_date='Mon Jun  6 21:31:50 CEST 2005' inverted='False' hash='20050606193150-891bb-dad36762ac41517fe0a9136ea14fff32b2930f0d.gz'>
        <name>CarpetWeb: Update web pages</name>
        <comment>
Update the web pages.
Explain stable and development versions better.
Update darcs binaries and documentation.</comment>
    <summary>
    <add_file>
    Carpet/CarpetWeb/binaries/darcs-1.0.3-static-linux-i386.gz
    </add_file>
    <remove_file>
    Carpet/CarpetWeb/binaries/darcs-1.0.3-static-linux-i386.gz
    </remove_file>
    <remove_file>
    Carpet/CarpetWeb/doc/darcs-1.0.2.ps.gz
    </remove_file>
    <add_file>
    Carpet/CarpetWeb/doc/darcs-1.0.3.ps.gz
    </add_file>
    <modify_file>
    Carpet/CarpetWeb/get-carpet-darcs.html<removed_lines num='68'/><added_lines num='128'/>
    </modify_file>
    <modify_file>
    Carpet/CarpetWeb/index.html<removed_lines num='56'/><added_lines num='17'/>
    </modify_file>
    <modify_file>
    Carpet/CarpetWeb/olds.html<removed_lines num='1'/><added_lines num='22'/>
    </modify_file>
    <modify_file>
    Carpet/CarpetWeb/work-with-darcs.html<removed_lines num='4'/><added_lines num='4'/>
    </modify_file>
    </summary>
</patch>
</changelog>
"""

    def testAddAndRemove(self):
        "Verify if the parser annihilate (add A)+(remove A)"

        log = StringIO(self.ADD_THEN_REMOVE_TEST)
        csets = changesets_from_darcschanges(log)

        cset = csets.next()

        self.assertEqual([], [e for e in cset.entries
                              if e.name == 'Carpet/CarpetWeb/binaries/darcs-1.0.3-static-linux-i386.gz'])
