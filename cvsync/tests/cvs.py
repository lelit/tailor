#  -*- Python -*- -*- coding: iso-8859-1 -*-
# :Progetto: Bice -- Test CVS functionalities
# :Sorgente: $HeadURL: http://svn.bice.dyndns.org/progetti/wip/tools/cvsync/tests/cvs.py $
# :Creato:   mar 20 apr 2004 16:48:34 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Modifica: $LastChangedDate: 2004-05-10 16:43:49 +0200 (lun, 10 mag 2004) $
# :Fatta da: $LastChangedBy: lele $
# 

from unittest import TestCase, TestSuite
from cvsync.shwrap import SystemCommand

class CvsInit(SystemCommand):
    COMMAND = "cvs -q -d %(repos)s init"

class CvsImport(SystemCommand):
    COMMAND = "cvs -Q -d %(repos)s import -m 'Initial' test lele start"

class CvsCheckout(SystemCommand):
    COMMAND = "cvs -Q -d %(repos)s checkout test"

class CvsAdd(SystemCommand):
    COMMAND = "cvs -Q add %(entry)s"

class CvsRemove(SystemCommand):
    COMMAND = "cvs -Q remove %(entry)s"

class CvsCommit(SystemCommand):
    COMMAND = "cvs -Q commit -m'%(msg)s' >/dev/null"

class CvsAdd(SystemCommand):
    COMMAND = "cvs -Q add %(entry)s"


class CvsRepos(object):
    """A test CVS repository.
    """
    
    def __init__(self, reposdir=None):
        """Initialize a CvsRepos instance.
        """

        if not reposdir:
            from tempfile import mkdtemp
            reposdir = mkdtemp(prefix="rep")
            
        self.reposdir = reposdir
        self.initialize()
        self.populateInitial()

    def cleanup(self):
        """Remove the repository from the filesystem.
        """
        
        from shutil import rmtree

        rmtree(self.reposdir)

    def initialize(self):
        """Initialize this new CVS repository.
        """
        
        initcmd = CvsInit()
        initcmd(repos=self.reposdir)
        assert (not initcmd.exit_status)
        
    def populateInitial(self):
        """Introduce some initial content.
        """
        
        from tempfile import mkdtemp
        from os import mkdir
        from os.path import join
        from shutil import rmtree

        tmpdir = mkdtemp()
        try:
            open(join(tmpdir, 'a.txt'), 'w').write('file a\n'*10)
            open(join(tmpdir, 'b.txt'), 'w').write('file b\n'*10)
            subdir = join(tmpdir, 'subdir')
            mkdir(subdir)
            open(join(subdir, 'c.txt'), 'w').write('file c\n'*10)
            open(join(subdir, 'e.txt'), 'w').write('file e\n'*10)

            cicmd = CvsImport(working_dir=tmpdir)
            cicmd(repos=self.reposdir)
            assert (not cicmd.exit_status)
        finally:
            rmtree(tmpdir)


class CvsTestWC(object):
    """A test working copy.
    """
    
    def __init__(self, repos, tmpdir=None):
        """Initialize a CvsTestWC instance.
        """

        from os.path import join

        self.repos = repos

        self.modified = []
        self.added = []
        self.removed = []
        self.changed = []
        self.added_dirs = []
        self.removed_dirs = []        

        if not tmpdir:
            from tempfile import mkdtemp
            tmpdir = mkdtemp(prefix="wc")
            
        cocmd = CvsCheckout(working_dir=tmpdir)
        cocmd(repos=repos.reposdir)
        assert (not cocmd.exit_status)
        
        self.wcdir = join(tmpdir, 'test')

    def commit(self, msg):
        """Execute a ``cvs commit``.
        """

        cvsci = CvsCommit(working_dir=self.wcdir)
        cvsci(msg=msg)

    def randomChanges(self, msg, passes=1):
        """Perform random changes, then commit.
        """

        from scrambler import Scrambler
        
        scrambler = Scrambler(self.wcdir, 0)
        for i in range(passes):
            scrambler(notify=self)

        if msg:
            cvsadd = CvsAdd(working_dir=self.wcdir)
            for file in self.added_dirs:
                cvsadd(entry=file)
            for file in self.added:
                cvsadd(entry=file)

            cvsrm = CvsRemove(working_dir=self.wcdir)
            for file in self.removed:
                cvsrm(entry=file)
            for file in self.removed_dirs:
                cvsrm(entry=file)

            self.commit(msg)           
            
    def addFile(self, entry, newcontent='New file content\n'):
        """Execute a ``cvs add``.
        """

        from os.path import exists, join

        name = join(self.wcdir, path)
        if not exists(name):
            f = open(name, 'w')
            f.write(newcontent)
            f.close()
            
        cvsadd = CvsCommit(working_dir=self.wcdir)
        cvsadd(entry=entry)
        
FAKECVSUPDATE_LOG = """\
cvs update: Updating .
cvs update: warning: subdir/b.txt was lost
cvs update: Updating subdir
cvs update: warning: languages/pt-br.py is not (any longer) pertinent
U a.txt
P b.txt
cvs update: warning: subdir/pt-br.py is not (any longer) pertinent
M subdir/c.txt
cvs server: subdir/form.pt is no longer in the repository
RCS file: /cvsroot/subdir/e.txt,v
retrieving revision 1.70
retrieving revision 1.73
Merging differences between 1.70 and 1.73 into e.txt
rcsmerge: warning: conflicts during merge
cvs update: conflicts found in subdir/e.txt
C subdir/e.txt
cvs update: subdir/htmlfragment.py is no longer in the repository"""

class BasicCvsTest(TestCase):
    """Perform some basic tests of the wrapper.
    """

    def __init__(self, methodName):
        TestCase.__init__(self, methodName)

        self.repos = CvsRepos()
        self.wc = CvsTestWC(self.repos)

    def testEntries(self):
        """Verify basic CVS/Entries functionalities
        """
        
        from cvsync.cvs import CvsEntries

        # NOTE: this must be the first test (ie, alphabetically the first
        #       method!) to be sure of the following.
        
        entries = CvsEntries(self.wc.wcdir)
        self.assertEqual(len(entries.files), 2)
        self.assertEqual(len(entries.directories), 1)
        self.assertEqual(entries.deleted, False)

        self.assertEqual(entries.getFileInfo('a.txt').cvs_version, '1.1.1.1')
        
    def testModifications(self):
        """Verify tracking of applied changes
        """
        
        from cvsync.cvs import CvsEntries

        before = CvsEntries(self.wc.wcdir)
        self.wc.randomChanges("Testing CvsEntries", passes=5)
        after = CvsEntries(self.wc.wcdir)

        self.assertNotEqual(before, after)
        
        for file in self.wc.added:
            oldinfo = before.getFileInfo(file)
            newinfo = after.getFileInfo(file)
            self.failUnless(oldinfo is None, '%s is new' % file)
            self.failUnless(not newinfo is None, '%s is new' % file)
            self.assertEqual(newinfo.cvs_version, '1.1', '%s is new' % file)
            
        for file in self.wc.removed:
            oldinfo = before.getFileInfo(file)
            newinfo = after.getFileInfo(file)
            self.failUnless(not oldinfo is None, '%s was removed' % file)
            self.failUnless(newinfo is None, '%s was removed' % file)
            if file in self.wc.modified:
                self.wc.modified.remove(file)
                
        for file in self.wc.modified:
            newinfo = after.getFileInfo(file)
            self.failUnless(not newinfo is None, '%s was modified' % file)
            self.assertNotEqual(after.getFileInfo(file).cvs_version,
                                '1.1.1.1', '%s was modified' % file)
            
        self.assertEqual(self.wc.removed_dirs,
                         after.removedDirectories(before))
        self.assertEqual(self.wc.added_dirs,
                         after.addedDirectories(before))

    def testUpdateLogParser(self):
        """Verify that the parser groks with ``cvs update`` log.
        """
        
        from cvsync.cvs import CvsWorkingDir

        cvswc = CvsWorkingDir(self.wc.wcdir)
        # the parser expects the \n at the end of each line
        lines = [line+'\n' for line in FAKECVSUPDATE_LOG.split('\n')]
        cvswc.parseUpdateLog(lines, relax=False)

        self.assertEqual(cvswc.modified, ['a.txt',
                                          'b.txt',
                                          'subdir/c.txt', ])
        self.assertEqual(cvswc.conflicts, ['subdir/e.txt',])
        self.assertEqual(cvswc.removed, ['languages/pt-br.py',
                                         'subdir/pt-br.py',
                                         'subdir/form.pt',
                                         'subdir/htmlfragment.py'])
