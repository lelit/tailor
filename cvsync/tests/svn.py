#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: cvsync -- svn commands
# :Sorgente: $HeadURL$
# :Creato:   mer 26 mag 2004 23:53:05 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Modifica: $LastChangedDate$
# :Fatta da: $LastChangedBy$
# 
__docformat__ = 'reStructuredText'

from unittest import TestCase, TestSuite
from cvsync.shwrap import SystemCommand
from cvsync.svn import SvnWorkingDir

class SvnAdminCreate(SystemCommand):
    COMMAND = "svnadmin create %(repository)s"


class SvnAdminLoad(SystemCommand):
    COMMAND = "svnadmin load --quiet %(repository)s < %(dumpfile)s"


class TestRepository(object):
    """A simple wrapper to a svn repository."""

    def __init__(self, path):
        from os.path import abspath, join, exists

        self.repospath = path
        self.reposurl = "file://" + abspath(path)

        if not exists(path):
            self.__createTestRepository()

    def __createTestRepository(self):
        from os.path import join, dirname
        
        svnc = SvnAdminCreate()
        svnc(repository=self.repospath)

        svnl = SvnAdminLoad()
        svnl(dumpfile=join(dirname(__file__),'testrepo.dump'),
             repository=self.repospath)


class SvnBasicTest(TestCase):
    """Test basic svn related functionalities."""
    
    def __init__(self, methodName):
        TestCase.__init__(self, methodName)

        repos = '/tmp/cvsync.test'
        self.repos = TestRepository(repos)
        wc = '/tmp/cvsync.wc'
        self.wc = SvnWorkingDir(wc)

    def testCheckout(self):
        """Verify that svn checkout returns right info"""

        info = self.wc.checkout(self.repos.reposurl+'@0')
        self.assertEqual(info['URL'], self.repos.reposurl)
        self.assertEqual(info['Revision'], '0')
    
class SvnLogTest(TestCase):
    """Test `svn log` parse functionality."""

    def __init__(self, methodName):
        from os.path import exists
        
        TestCase.__init__(self, methodName)

        repos = '/tmp/cvsync.test'
        self.repos = TestRepository(repos)
        wc = '/tmp/cvsync.wc'
        self.wc = SvnWorkingDir(wc)
        if not exists(wc):
            self.wc.checkout(self.repos.reposurl + '@0')
        
    def testLogParser(self):
        """Verify the `svn log` parser"""
        
        revisions = self.wc.log()
        self.assertEqual(len(revisions), 3)
        
        self.assertEqual(revisions[0].revision, '1')
        self.assertEqual(revisions[0].author, 'lele')
        self.assertEqual(revisions[0].date, '2004-05-31T14:38:46.210103Z')
        self.assertEqual(revisions[0].paths, [
            (u'/DirA/FileD.txt', u'A'),
            (u'/FileC.txt', u'A'),
            (u'/DirA/FileE.txt', u'A'),
            (u'/FileA.txt', u'A'),
            (u'/DirA', u'A'),
            (u'/FileB.txt', u'A')])
        
        self.assertEqual(revisions[1].revision, '2')
        self.assertEqual(revisions[1].author, 'lele')
        self.assertEqual(revisions[1].date, '2004-05-31T14:40:58.583701Z')
        self.assertEqual(revisions[1].paths, [
            (u'/DirA/FileD.txt', u'M'),
            (u'/FileC.txt', u'M'),
            (u'/FileA.txt', u'M')])
        
        self.assertEqual(revisions[2].revision, '3')
        self.assertEqual(revisions[2].author, 'lele')
        self.assertEqual(revisions[2].date, '2004-06-01T13:52:35.711425Z')
        self.assertEqual(revisions[2].paths, [
            (u'/FileC.txt', u'D'),
            (u'/file_a.txt', (u'A', u'/FileA.txt', u'2')),
            (u'/FileA.txt', u'D'),
            (u'/file_b.txt', (u'A', u'/FileB.txt', u'2')),
            (u'/FileB.txt', u'D'),
            (u'/file_c.txt', (u'A', u'/FileC.txt', u'2'))])
