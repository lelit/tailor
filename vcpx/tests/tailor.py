#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Frontend specific tests
# :Creato:   mar 03 ago 2004 01:53:21 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# 

from unittest import TestCase, TestSuite
from datetime import datetime
from StringIO import StringIO
from vcpx.tailor import relpathto

class RelPathToTest(TestCase):
    """Tests for the relpathto function"""

    def testRelPathTo(self):
        """Verify relpathto() computes right relative paths"""
        
        self.assertEqual(relpathto('project', '.'), 'project')
        self.assertEqual(relpathto('project', 'sub/dir'), '../../project')
        self.assertEqual(relpathto('/tmp/project', '/usr/tmp/dir'),
                         '../../../tmp/project')
