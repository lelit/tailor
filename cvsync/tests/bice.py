#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: Bice -- Test peculiarità Bice
# :Sorgente: $HeadURL: http://svn.bice.dyndns.org/progetti/wip/tools/cvsync/tests/bice.py $
# :Creato:   sab 08 mag 2004 15:38:56 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Modifica: $LastChangedDate: 2004-05-08 16:25:42 +0200 (sab, 08 mag 2004) $
# :Fatta da: $LastChangedBy: lele $
# 

from unittest import TestCase, TestSuite

_products = {}
def bootstrapProductTest(product, uri):
    """
    Just register in a dictionary the result, for testing purposes.
    """

    _products[product] = uri

class BicePeculiaritiesTest(TestCase):
    """Perform basic tests on Bice."""

    def testGeneratedURIs(self):
        """Verify the URI generated for the bootstrap"""
        
        from cvsync import bice

        bice.initProduct = bice.bootstrapProduct = bootstrapProductTest

        bice.register3rdProduct('TextIndexNG2')
        self.assertEqual(_products.get('TextIndexNG2'),
                         'http://svn.bice.dyndns.org/progetti/3rd/textindexng/HEAD/TextIndexNG2')
        
        bice.registerUserProduct('AdLSkin', user="lele", bootstrap=False)
        self.assertEqual(_products.get('AdLSkin'),
                         'http://svn.bice.dyndns.org/progetti/usr/lele/AdLSkin')
        
        bice.register3rdProduct('GroupUserFolder', cvstag='1.x')
        self.assertEqual(_products.get('GroupUserFolder'),
                         'http://svn.bice.dyndns.org/progetti/3rd/groupuserfolder/1.x/GroupUserFolder')
        
        bice.registerOurProduct('Archetypes', cvstag='1.3',
                                subdirs=['Archetypes', 'generator',
                                         'PortalTransforms', 'validation'])
        for s in ['Archetypes', 'generator', 'PortalTransforms', 'validation']:
            self.assertEqual(_products.get(s),
                             'http://svn.bice.dyndns.org/progetti/our/archetypes/1.3/%s' % s)

        bice.register3rdProduct('CMF', cvstag='1.4.3',
                                subdirs=['CMFCalendar', 'CMFCore',
                                         'CMFDefault', 'CMFTopic',
                                         'DCWorkflow'])
        
        for s in ['CMFCalendar', 'CMFCore',
                  'CMFDefault', 'CMFTopic',
                  'DCWorkflow']:
            self.assertEqual(_products.get(s),
                             'http://svn.bice.dyndns.org/progetti/3rd/cmf/1.4.3/%s' % s)
        
