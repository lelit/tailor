#  -*- Python -*- -*- coding: iso-8859-1 -*-
# :Progetto: Bice -- Sync CVS->SVN: dettagli SVN
# :Sorgente: $HeadURL: http://svn.bice.dyndns.org/progetti/wip/tools/cvsync/svn.py $
# :Creato:   sab 10 apr 2004 16:48:21 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Modifica: $LastChangedDate: 2004-05-15 01:29:52 +0200 (sab, 15 mag 2004) $
# :Fatta da: $LastChangedBy: lele $
# 

"""A little layer above the Subversion world.

   Note: this script does not use the svn bindings, because they're not up
   to the task.  After revision 523 the support was completely removed.
"""

__docformat__ = 'reStructuredText'

from shwrap import SystemCommand

class SvnUpdate(SystemCommand):
    COMMAND = "svn update %(entry)s"


class SvnCommit(SystemCommand):
    COMMAND = "svn commit --quiet %(message)s %(logfile)s %(entry)s"

    def __call__(self, output=None, dry_run=False, **kwargs):
        logfile = kwargs.get('logfile')
        if logfile:
            kwargs['logfile'] = '--file %s' % logfile
        else:
            kwargs['logfile'] = ''

            message = kwargs.get('message')
            if message:
                kwargs['message'] = '--message %s' % repr(message)
            else:
                kwargs['message'] = ''
        
        return SystemCommand.__call__(self, output=output,
                                      dry_run=dry_run, **kwargs)


class SvnAdd(SystemCommand):
    COMMAND = "svn add --quiet --no-auto-props %(entry)s"


class SvnRemove(SystemCommand):
    COMMAND = "svn remove --quiet --force %(entry)s"


class SvnInfo(SystemCommand):
    COMMAND = "svn info %(entry)s"


class SvnCopy(SystemCommand):
    COMMAND = "svn copy --quiet --revision %(rev)s %(source)s %(dest)s"


class InternalError(Exception): pass

class SvnExport(SystemCommand):
    COMMAND = "svn export --revision %(rev)s %(source)s %(dest)s"

    def __call__(self, output=None, dry_run=False, **kwargs):
        """Execute the call and return the exported revision."""
        
        if dry_run:
            return
        
        output = SystemCommand.__call__(self, output=True,
                                        dry_run=dry_run,
                                        **kwargs)

        for line in output:
            if line.startswith('Exported revision '):
                return line[18:-2]

        raise InternalError('The export command did not end with the expected '
                            '"Exported revision XXX."')

class SvnMerge(SystemCommand):
    COMMAND = "svn merge %(dry)s--revision %(startrev)s:%(endrev)s %(source)s %(dest)s"
    
    def __call__(self, output=None, dry_run=False, **kwargs):
        if dry_run:
            kwargs['dry'] = '--dry-run '
        else:
            kwargs['dry'] = ''
        return SystemCommand.__call__(self, output=output,
                                      dry_run=dry_run, **kwargs)


class SvnPropGet(SystemCommand):
    COMMAND = "svn propget %(property)s %(entry)s"

    
class SvnPropSet(SystemCommand):
    COMMAND = "svn propset --quiet %(property)s %(value)s %(entry)s"


class SvnLog(SystemCommand):
    COMMAND = "svn log --quiet --revision %(startrev)s:HEAD %(source)s"


class SvnDiff(SystemCommand):
    COMMAND = "svn diff --old %(other)s@%(otherrev)s --new ."

    
def getHeadRevision(source, baserev):
    """Using ``svn log`` determine the HEAD revision of a source."""
    
    svnlog = SvnLog()
    out = svnlog(output=True, startrev=baserev, source=source)
    head = baserev
    for line in out:
        if line.startswith('r'):
            head = line[1:line.index(' ')]
    return head

class SvnWorkingDir(object):
    """Represent a SVN working directory."""

    __slots__ = ('root',)

    def __init__(self, root):
        """Initialize a SvnWorkingDir instance."""
        
        self.root = root
        """The directory in question."""

    def _makeabs(self, mayberel):
        from os.path import join, isabs

        if not isabs(mayberel):
            return join(self.root, mayberel)
        else:
            return mayberel
        
    def update(self):
        """Bring this directory up to its HEAD revision in the repository."""

        svnup = SvnUpdate()
        svnup(entry=self.root)
    
    def commit(self, logfile=None, message=None):
        """Commit the changes."""

        svnci = SvnCommit()
        svnci(logfile=logfile, message=message, entry=repr(self.root))
        return svnci.exit_status

    def add(self, entry):
        """Add an entry."""

        svnadd = SvnAdd()
        svnadd(entry=repr(self._makeabs(entry)))

    def remove(self, entry):
        """Remove an entry."""

        svnrm = SvnRemove()
        svnrm(entry=repr(self._makeabs(entry)))

    def info(self, entry):
        """Return information about an entry."""

        svni = SvnInfo()
        output = svni(output=True, entry=self._makeabs(entry))
        res = {}
        for l in output:
            l = l[:-1]
            if l:
                key, value = l.split(':', 1)
                res[key] = value[1:]
        return res

    def copy(self, uri, dest, dry_run=False):
        """Copy a source URI to dest."""

        from os.path import dirname, commonprefix
            
        if '@' in uri:
            src,rev = uri.split('@')
        else:
            src = uri
            rev = "HEAD"

        info = self.info(dirname(dest))
        prefix = commonprefix([info['URL'], src])
        
        if ':' in prefix and prefix.count('/')>2:
            # same repository

            svnc = SvnCopy()
            svnc(source=src, dest=self._makeabs(dest), rev=rev,
                 dry_run=dry_run)

            info = self.info(dest)
        else:
            # other: sigh, svn does not implement extra-repos copy :-[

            svne = SvnExport()
            effective_rev = svne(source=src, dest=self._makeabs(dest), rev=rev,
                                 dry_run=dry_run)

            svna = SvnAdd()
            svna(entry=self._makeabs(dest))
            
            info = self.info(dest)

            # Return a faked info, with just what the caller needs :-|
            info['Copied From URL'] = src
            info['Copied From Rev'] = effective_rev
            
        return info
    
    def getProperty(self, entry, prop):
        """Return the given property on the entry."""

        svnpg = SvnPropGet()
        out = svnpg(output=True, entry=self._makeabs(entry), property=prop)
        return out.readline()[:-1]

    def setProperty(self, entry, prop, value):
        """Set the given property on the entry to the specified value."""

        svnps = SvnPropSet()
        svnps(property=prop, entry=self._makeabs(entry), value=repr(value))

    def merge(self, uri, startrev, endrev, dest, dry_run=False):
        """Perform the merge."""

        svnm = SvnMerge()
        out = svnm(output=True, startrev=startrev, endrev=endrev,
                   source=uri, dest=dest, dry_run=dry_run)

        merged = False
        if not dry_run:
            for line in out:
                if line.startswith('C '):
                    print "CONFLICT:", line
                merged = True
            
        return merged

    def diff(self, uri, rev):
        """Perform a diff against another tree."""

        svnd = SvnDiff(working_dir=self.root)
        svnd(other=uri, otherrev=rev)
