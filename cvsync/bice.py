#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: Bice -- Bice Development Team details
# :Sorgente: $HeadURL: http://svn.bice.dyndns.org/progetti/wip/tools/cvsync/bice.py $
# :Creato:   sab 08 mag 2004 03:31:42 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Modifica: $LastChangedDate: 2004-05-08 18:16:38 +0200 (sab, 08 mag 2004) $
# :Fatta da: $LastChangedBy: lele $
#

"""
This module collects Bice specific structures and facilities.

It's commonly used to bootstrap a new project, populating a "Products"
directory in this way::

  from cvsync.bice import setProductDir, \
                          register3rdProduct, \
                          registerOurProduct, \
                          registerUserProduct

  setProductDir('Products')
  
  register3rdProduct('TextIndexNG2')
  registerUserProduct('AdLSkin')
  register3rdProduct('GroupUserFolder')
  registerOurProduct('Archetypes', cvstag='1.3',
                     subdirs=['Archetypes', 'generator',
                              'PortalTransforms', 'validation'])

The ``setProductDir`` set the target directory, eventually creating
it, and should be called as the very first step of the script.  If not
called, the machinery assumes an already existing "Products" versioned
directory.
"""

__docformat__ = 'reStructuredText'

BASEURI = "http://svn.bice.dyndns.org/progetti/"
"""The root URI of the repository"""

PRODUCTS_DIR = "Products"
"""The default target directory"""

ALIASES = {
    "TextIndexNG2": "textindexng",
    "CMFPlone": "plone",
    "PloneKeywordManager": "plonekeywordmgr",
    "PlacelessTranslationService": "pts",
    "DocFinderEverywhere": "docfinder",
    }
"""A dictionary that maps between a ProductName and the alias under which
it's stored in the "3rd" hierarchy"""

from tailor import Tailorizer
from os.path import join
from shwrap import SystemCommand

def bootstrapProduct(product, uri):
    """
    Bootstrap a product from the specified URI.
    """

    class Options:
        def __init__(self):
            self.dry_run = False
            self.message = ""

    options = Options()

    prodwc = join(PRODUCTS_DIR, product)
    tizer = Tailorizer(prodwc, uri)
    tizer.bootstrap(options)
    
def initProduct(product, uri):
    """
    Write upstream information, without bootstrapping the product.
    """

    prodwc = join(PRODUCTS_DIR, product)
    tizer = Tailorizer(prodwc, uri)
    tizer.setUpstreamInfo()
    
class BiceProduct(object):
    """
    An abstract product.
    """

    def __init__(self, name, revision=""):
        self.name = name
        if revision:
            self.revision = '@' + revision
        else:
            self.revision = ""

    def register(self, bootstrap=True):
        """
        Do the actual work.

        Cycle on the components of the product, and call the right function.
        """
        
        from os.path import join

        if bootstrap:
            func = bootstrapProduct
        else:
            func = initProduct
            
        components = self.components()
        for name, pathsegments in components:
            func(name, BASEURI + join(*pathsegments) + self.revision)
                
    def components(self):
        """
        Subclass responsibility.

        Should return a sequence or a generator of tuples of kind
        ('product-name', ('path', 'components'...)).
        """
        
        pass
    
class UserProduct(BiceProduct):
    """
    Represent a product kept under /usr/user-name/product-name.
    """

    ROOT = 'usr'
    """The name of the root directory under which this product lives."""
    
    def __init__(self, name, revision="", user='azazel'):
        BiceProduct.__init__(self, name, revision)
        self.user = user

    def components(self):
        """
        This kind of products are kept under a single directory in the
        user's home directory.  Return a single tuple describing that.
        """
        return ( (self.name, (self.ROOT, self.user, self.name)), )

class ThirdPartyProduct(BiceProduct):
    """
    Represent a third party product, under /3rd/prod-alias/CVSTAG/product-name
    or /3rd/prod-alias/CVSTAG/[subproducts...].
    """

    ROOT = '3rd'
    
    def __init__(self, name, revision="",
                 alias="", cvstag="HEAD", subdirs=None):
        BiceProduct.__init__(self, name, revision)
        self.alias = alias or ALIASES.get(name, name.lower())
        self.cvstag = cvstag
        self.subdirs = subdirs or [name]

    def components(self):
        """
        Generate a sequence of tuples describing each subcomponent of
        the product.
        """
        
        for d in self.subdirs:
            yield d, (self.ROOT, self.alias, self.cvstag, d)

class OurTailoredProduct(ThirdPartyProduct):
    """
    Represent a third party product once it's been tailored by us, under
    the /our subtree in the repository, with the usual naming scheme.
    """
    
    ROOT = 'our'
    
def registerUserProduct(name, bootstrap=True, **kw):
    """Facility for registering a UserProduct"""
    
    UserProduct(name, **kw).register(bootstrap)

def register3rdProduct(name, bootstrap=True, **kw):
    """Facility for registering a ThirdPartyProduct"""
    
    ThirdPartyProduct(name, **kw).register(bootstrap)

def registerOurProduct(name, bootstrap=True, **kw):
    """Facility for registering a OurTailoredProduct"""
    
    OurTailoredProduct(name, **kw).register(bootstrap)

class SvnMkdir(SystemCommand):
    COMMAND = "svn mkdir %(dir)s"

def setProductDir(dir):
    """
    Set the target directory, creating it with ``svn mkdir`` if it
    does not exist.
    """
    
    from os.path import exists

    global PRODUCTS_DIR
    PRODUCTS_DIR = dir

    if not exists(dir):
        svnmk = SvnMkdir()
        svnmk(dir=dir)
        
if __name__ == '__main__':
    register3rdProduct('TextIndexNG2', alias='textindexng')
    register3rdProduct('TextIndexNG2')
     
    registerUserProduct('AdLSkin')
    registerUserProduct('AdLSkin', user="lele", bootstrap=False)
     
    registerOurProduct('GroupUserFolder')
    registerOurProduct('Archetypes', cvstag='1.3',
                       subdirs=['Archetypes', 'generator',
                                'PortalTransforms', 'validation'])
    
