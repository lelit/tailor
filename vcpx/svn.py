#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Subversion details
# :Creato:   ven 18 giu 2004 15:00:52 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
#

__docformat__ = 'reStructuredText'

from cvsync.shwrap import SystemCommand
from source import UpdatableSourceWorkingDir
from target import SyncronizableTargetWorkingDir


class SvnUpdate(SystemCommand):
    COMMAND = "svn update --revision %(revision)s %(entry)s"


class SvnInfo(SystemCommand):
    COMMAND = "svn info %(entry)s"

    def __call__(self, output=None, dry_run=False, **kwargs):
        output = SystemCommand.__call__(self, output=True,
                                        dry_run=dry_run,
                                        entry=entry)
        res = {}
        for l in output:
            l = l[:-1]
            if l:
                key, value = l.split(':', 1)
                res[key] = value[1:]
        return res

                 
class SvnPropGet(SystemCommand):
    COMMAND = "svn propget %(property)s %(entry)s"

    
class SvnPropSet(SystemCommand):
    COMMAND = "svn propset --quiet %(property)s %(value)s %(entry)s"


class SvnLog(SystemCommand):
    COMMAND = "svn log %(quiet)s %(xml)s --revision %(startrev)s:%(endrev)s %(entry)s"
    
    def __call__(self, output=None, dry_run=False, **kwargs):
        quiet = kwargs.get('quiet', True)
        if quiet == True:
            kwargs['quiet'] = '--quiet'
        elif quiet == False:
            kwargs['quiet'] = ''
            
        xml = kwargs.get('xml', False)
        if xml:
            kwargs['xml'] = '--xml'
            output = True
        else:
            kwargs['xml'] = ''

        startrev = kwargs.get('startrev')
        if not startrev:
            kwargs['startrev'] = 'BASE'

        endrev = kwargs.get('endrev')
        if not endrev:
            kwargs['endrev'] = 'HEAD'

        output = SystemCommand.__call__(self, output=output,
                                        dry_run=dry_run, **kwargs)

        if xml:
            # parse the output and return the result
            pass

        return output


class SvnCheckout(SystemCommand):
    COMMAND = "svn co --quiet --revision %(revision)s %(repository)s %(wc)s"

    
class SvnCommit(SystemCommand):
    COMMAND = "svn commit --quiet %(logfile)s %(entries)s"

    def __call__(self, output=None, dry_run=False, **kwargs):
        logfile = kwargs.get('logfile')
        if not logfile:
            from tempfile import NamedTemporaryFile

            log = NamedTemporaryFile(bufsize=0)
            logmessage = kwargs.get('logmessage')
            if logmessage:
                print >>log, logmessage
            
            kwargs['logfile'] = log.name
        
        return SystemCommand.__call__(self, output=output,
                                      dry_run=dry_run, **kwargs)


class SvnAdd(SystemCommand):
    COMMAND = "svn add --quiet --non-recursive --no-auto-props %(entry)s"


class SvnRemove(SystemCommand):
    COMMAND = "svn remove --quiet --force %(entry)s"


class SvnMv(SystemCommand):
    COMMAND = "svn mv --quiet %(old)s %(new)s"

    
class SvnCheckout(SystemCommand):
    COMMAND = "svn co --quiet --revision %(revision)s %(repository)s %(wc)s"

    
class SvnWorkingDir(UpdatableSourceWorkingDir, SyncronizableTargetWorkingDir):

    ## UpdatableSourceWorkingDir

    def _getUpstreamChangesets(self, root, startfrom_rev=None):
        svnlog = SvnLog(working_dir=root)
        log = svnlog(quiet='--verbose', output=True, xml=True, entry='.')

        return self.__parseSvnLog(log)

    def __parseSvnLog(self, log):
        """Return an object representation of the ``svn log`` thru HEAD."""

        from xml.sax import parseString
        from xml.sax.handler import ContentHandler

        class SvnXMLLogHandler(ContentHandler):
            def __init__(self):
                self.changesets = []
                self.current = None
                self.current_field = []

            def startElement(self, name, attributes):
                if name == 'logentry':
                    self.current = {}
                    self.current['revision'] = attributes['revision']
                    self.current['entries'] = []
                elif name in ['author', 'date', 'msg']:
                    self.current_field = []
                elif name == 'path':
                    self.current_field = []
                    if attributes.has_key('copyfrom-path'):
                        self.current_path_action = (
                            attributes['action'],
                            attributes['copyfrom-path'][1:], # make it relative
                            attributes['copyfrom-rev'])
                    else:
                        self.current_path_action = attributes['action']

            def endElement(self, name):
                if name == 'logentry':
                    # Sort the paths to make tests easier
                    self.current['entries'].sort()
                    self.changesets.append(ChangeSet(**self.current))
                    self.current = None
                elif name in ['author', 'date', 'msg']:
                    self.current[name] = ''.join(self.current_field))
                elif name == 'path':
                    entry = ChangesetEntry(''.join(self.current_field)[1:])
                    if type(self.current_path_action) == type(''):
                        entry.action_kind = self.current_path_action
                    else:
                        entry.action_kind = entry.RENAMED
                        entry.old_name = self.current_path_action[1]

                    self.current['entries'].append(entry)

            def characters(self, data):
                self.current_field.append(data)

        
        handler = SvnXMLLogHandler()
        parseString(log.getvalue(), handler)
        return handler.changesets
    
    def _applyChangeset(self, root, changeset):
        svnup = SvnUpdate(working_dir=root)
        svnup(entry='.', revision=changeset.revision)       
        
    ## SyncronizableTargetWorkingDir

    def _addEntry(self, root, entry):
        """
        Add a new entry, maybe registering the directory as well.
        """

        from os.path import split, join, exists

        basedir = split(entry)[0]
        if basedir and not exists(join(basedir, '.svn')):
            self._addEntry(root, basedir)

        c = SvnAdd(working_dir=root)
        c(entry=entry)

    def _checkoutUpstreamRevision(self, basedir, repository, module, revision):
        """
        Concretely do the checkout of the upstream revision.
        """
        
        svnco = SvnCheckout(working_dir=basedir)
        svnco(repository=repository, wc=module, revision=revision)
        
    def _commit(self, root, author, remark, changelog=None, entries=None):
        """
        Commit the changeset.
        """

        c = SvnCommit(working_dir=root)
        
        logmessage = remark + '\n'
        if changelog:
            logmessage = logmessage + changelog + '\n'
            
        if entries:
            entries = ' '.join(entries)
        else:
            entries = '.'
            
        c(logmessage=logmessage, entries=entries)
        
    def _removeEntry(self, root, entry):
        """
        Remove an entry.
        """

        c = SvnRemove(working_dir=root)
        c(entry=entry)

    def _renameEntry(self, root, oldentry, newentry):
        """
        Rename an entry.
        """

        c = SvnMv(working_dir=root)
        c(old=oldentry, new=newentry)

    def _initializeWorkingDir(self, root):
        """
        Do whatever is needed to put the given directory under revision
        control.
        """
        
        raise "%s should override this method" % self.__class__
