# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Mercurial native backend
# :Creato:   dom 11 set 2005 22:58:38 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
#            Brendan Cully <brendan@kublai.com>
# :Licenza:  GNU General Public License
#

"""
This module implements the backends for Mercurial, using its native API
instead of thru the command line.
"""

__docformat__ = 'reStructuredText'

from mercurial import ui, hg, cmdutil, commands

from vcpx.repository import Repository
from vcpx.source import UpdatableSourceWorkingDir
from vcpx.target import SynchronizableTargetWorkingDir


class HgRepository(Repository):
    METADIR = '.hg'

    def _load(self, project):
        Repository._load(self, project)
        ppath = project.config.get(self.name, 'python-path')
        if ppath:
            from sys import path

            if ppath not in path:
                path.insert(0, ppath)
        self.EXTRA_METADIRS = ['.hgtags']

    def _validateConfiguration(self):
        """
        Mercurial expects all data to be in utf-8, so we disallow other encodings
        """
        Repository._validateConfiguration(self)

        if self.encoding.upper() != 'UTF-8':
            self.log.warning("Forcing UTF-8 encoding instead of " + self.encoding)
            self.encoding = 'UTF-8'


class HgWorkingDir(UpdatableSourceWorkingDir, SynchronizableTargetWorkingDir):
    # UpdatableSourceWorkingDir
    def _checkoutUpstreamRevision(self, revision):
        """
        Initial checkout (hg clone)
        """

        from os import mkdir, rename, rmdir
        from os.path import exists, join

        self._getUI()
        # We have to clone the entire repository to be able to pull from it
        # later. So a partial checkout is a full clone followed by an update
        # directly to the desired revision.

        # If the basedir does not exist, create it
        if not exists(self.repository.basedir):
            mkdir(self.repository.basedir)

        # clone it only if .hg does not exist
        if not exists(join(self.repository.basedir, ".hg")):
            # Hg won't check out into an existing directory
            checkoutdir = join(self.repository.basedir,".hgtmp")
            opts = self._defaultOpts('clone')
            opts['noupdate'] = True
            commands.clone(self._ui, self.repository.repository, checkoutdir,
                           **opts)
            rename(join(checkoutdir, ".hg"), join(self.repository.basedir,".hg"))
            rmdir(checkoutdir)
        else:
            # Does hgrc exist? If not, we write one
            hgrc = join(self.repository.basedir, ".hg", "hgrc")
            if not exists(hgrc):
                hgrc = file(hgrc, "w")
                hgrc.write("[paths]\ndefault = %s\ndefault-push = %s\n" %
                           (self.repository.repository,
                            self.repository.repository))
                hgrc.close()

        repo = self._getRepo()
        node = self._getNode(repo, revision)

        self.log.info('Extracting revision %r from %r into %r',
                      revision, self.repository.repository, self.repository.basedir)
        repo.update(node)

        return self._changesetForRevision(repo, revision)

    def _getUpstreamChangesets(self, sincerev):
        """Fetch new changesets from the source"""
        repo = self._getRepo()

        self._hgCommand('pull', 'default')

        from mercurial.node import bin
        for rev in xrange(repo.changelog.rev(bin(sincerev)) + 1,
                          repo.changelog.count()):
            yield self._changesetForRevision(repo, str(rev))

    def _applyChangeset(self, changeset):
        repo = self._getRepo()
        node = self._getNode(repo, changeset.revision)

        self.log.info('Updating to %r', changeset.revision)
        res = repo.update(node)

        # The following code is for backward compatibility: hg 0.9.5
        # raises an Abort exception instead of just returning a status;
        # but under 0.9.5 we reimplanted hg.clean() into repo.update():
        # hg.clean() performs a clobbering clean merge and thus does
        # not stop on that situation.
        if res:
            # Files in to-be-merged changesets not on the trunk will
            # cause a merge error on update. If no files are modified,
            # added, removed, or deleted, do update -C
            modified, added, removed, deleted = repo.changes()[0:4]
            conflicting = modified + added + removed + deleted
            if conflicting:
                return conflicting
            return repo.update(node, force=True)

    def _changesetForRevision(self, repo, revision):
        from datetime import datetime
        from vcpx.changes import Changeset, ChangesetEntry
        from vcpx.tzinfo import FixedOffset

        entries = []
        node = self._getNode(repo, revision)
        parents = repo.changelog.parents(node)
        nodecontent = repo.changelog.read(node)
        # hg 0.9.5+ returns a tuple of six elements, last seems useless for us
        (manifest, user, date, files, message) = nodecontent[:5]

        dt, tz = date
        date = datetime.fromtimestamp(dt, FixedOffset(-tz/60)) # note the minus sign!

        manifest = repo.manifest.read(manifest)

        # To find adds, we get the manifests of any parents. If a file doesn't
        # occur there, it's new.
        pms = {}
        for parent in repo.changelog.parents(node):
            pms.update(repo.manifest.read(repo.changelog.read(parent)[0]))

        # if files contains only '.hgtags', this is probably a tag cset.
        # Tailor appears to only support tagging the current version, so only
        # pass on tags that are for the immediate parents of the current node
        tags = None
        if files == ['.hgtags']:
            tags = [tag for (tag, tagnode) in repo.tags().iteritems()
                    if tagnode in parents]

        # Don't include the file itself in the changeset. It's only useful
        # to mercurial, and if we do end up making a tailor round trip
        # the nodes will be wrong anyway.
        if '.hgtags' in files:
            files.remove('.hgtags')
        if pms.has_key('.hgtags'):
            del pms['.hgtags']

        for f in files:
            e = ChangesetEntry(f)
            # find renames
            fl = repo.file(f)
            oldname = f in manifest and fl.renamed(manifest[f])
            if oldname:
                e.action_kind = ChangesetEntry.RENAMED
                e.old_name = oldname[0]
                # hg copy can copy the same file to multiple destinations
                # Currently this is handled as multiple renames. It would
                # probably be better to have ChangesetEntry.COPIED.
                if pms.has_key(oldname[0]):
                    pms.pop(oldname[0])
            else:
                if pms.has_key(f):
                    e.action_kind = ChangesetEntry.UPDATED
                else:
                    e.action_kind = ChangesetEntry.ADDED

            entries.append(e)

        for df in [file for file in pms.iterkeys()
                   if not manifest.has_key(file)]:
            e = ChangesetEntry(df)
            e.action_kind = ChangesetEntry.DELETED
            entries.append(e)

        from mercurial.node import hex
        revision = hex(node)
        return Changeset(revision, date, user, message, entries, tags=tags)

    def _getUI(self):
        try:
            return self._ui
        except AttributeError:
            project = self.repository.projectref()
            self._ui = ui.ui(project.verbose,
                             project.config.get(self.repository.name,
                                                'debug', False),
                             not project.verbose, False)
            return self._ui

    def _getRepo(self):
        try:
            return self._hg
        except AttributeError:
            # dirstate walker uses simple string comparison between
            # repo root and os.getcwd, so root should be canonified.
            from os.path import realpath

            ui = self._getUI()
            self._hg = hg.repository(ui=ui, path=realpath(self.repository.basedir),
                                     create=False)
            # Pick up repository-specific UI settings.
            self._ui = self._hg.ui

            # 0.9.5 repos does not have update()...
            if not hasattr(self._hg, 'update'):
                # Use clean(), to force a clean merge clobbering local changes
                self._hg.update = lambda n: hg.clean(self._hg, n)

            return self._hg

    def _getNode(self, repo, revision):
        """Convert a tailor revision ID into an hg node"""
        if revision == "HEAD":
            node = repo.changelog.tip()
        else:
            if revision == "INITIAL":
                rev = "0"
            else:
                rev = revision
            node = repo.changelog.lookup(rev)

        return node

    def _normalizeEntryPaths(self, entry):
        """
        Normalize the name and old_name of an entry.

        This implementation uses ``mercurial.util.normpath()``, since
        at this level hg is expecting UNIX style pathnames, with
        forward slash"/" as separator, also under insane operating systems.
        """

        from mercurial.util import normpath

        entry.name = normpath(self.repository.encode(entry.name))
        if entry.old_name:
            entry.old_name = normpath(self.repository.encode(entry.old_name))

    def _removeDirs(self, names):
        from os.path import isdir, join, normpath
        """Remove the names that reference a directory."""
        return [n for n in names
                if not isdir(join(self.repository.basedir, normpath(n)))]
        return notdirs

    def _addPathnames(self, names):
        from os.path import join

        notdirs = self._removeDirs(names)
        if notdirs:
            self.log.info('Adding %s...', ', '.join(notdirs))
            self._hg.add(notdirs)

    def _commit(self, date, author, patchname, changelog=None, names=[],
                tags = [], isinitialcommit = False):
        from calendar import timegm  # like mktime(), but returns UTC timestamp
        from os.path import exists, join, normpath

        encode = self.repository.encode

        logmessage = []
        if patchname:
            logmessage.append(patchname)
        if changelog:
            logmessage.append(changelog)
        if logmessage:
            self.log.info('Committing %r...', logmessage[0])
            logmessage = encode('\n'.join(logmessage))
        else:
            self.log.info('Committing...')
            logmessage = "Empty changelog"

        timestamp = timegm(date.utctimetuple())
        timezone  = date.utcoffset().seconds + date.utcoffset().days * 24 * 3600

        opts = {}
        opts['message'] = logmessage
        opts['user'] = encode(author)
        opts['date'] =  '%d %d' % (timestamp, -timezone) # note the minus sign!
        notdirs = self._removeDirs(names)
        if (not isinitialcommit) and len(notdirs) == 0 and \
               (tags is None or len(tags) == 0):
            # Empty changeset; make sure we still see it
            empty = open(join(self.repository.basedir, '.hgempty'), 'a')
            empty.write("\nEmpty original changeset by %s:\n" % author)
            empty.write(logmessage + "\n")
            empty.close()
            self._hg.add(['.hgempty'])
        self._hgCommand('commit', **opts)

    def _tag(self, tag, date, author):
        """ Tag the tip with a given identifier """
        # TODO: keep a handle on the changeset holding this tag? Then
        # we can extract author, log, date from it.

        # This seems gross. I don't get why I'm getting a unicode tag when
        # it's just ascii underneath. Something weird is happening in CVS.
        tag = self.repository.encode(tag)

        # CVS can't tell when a tag was applied so it tends to pass around
        # too many. We want to support retagging so we can't just ignore
        # duplicates. But we can safely ignore a tag if it is contained
        # in the commit history from tip back to the last non-tag commit.
        repo = self._getRepo()
        tagnodes = repo.tags().values()
        try:
            tagnode = repo.tags()[tag]
            # tag commit can't be merge, right?
            parent = repo.changelog.parents(repo.changelog.tip())[0]
            while parent in tagnodes:
                if tagnode == parent:
                    return
                parent = repo.changelog.parents(parent)[0]
        except KeyError:
            pass
        self._hgCommand('tag', tag)

    def _defaultOpts(self, cmd):
        # Not sure this is public. commands.parse might be, but this
        # is easier, and while dispatch is easiest, you lose ui.
        # findxxx() is not public, and to make that clear, hg folks
        # keep moving the function around...
        if hasattr(cmdutil, 'findcmd'):            # >= 0.9.4
            if cmdutil.findcmd.func_code.co_argcount == 2:     # 0.9.4
                def findcmd(cmd):
                    return cmdutil.findcmd(self._getUI(), cmd)
            elif cmdutil.findcmd.func_code.co_argcount == 3:   # 0.9.5
                def findcmd(cmd):
                    return cmdutil.findcmd(self._getUI(), cmd, commands.table)
        elif hasattr(commands, 'findcmd'):         # < 0.9.4
            if commands.findcmd.func_code.co_argcount == 1:
                findcmd = commands.findcmd
            else:
                def findcmd(cmd):
                    return commands.findcmd(self._getUI(), cmd)
        elif hasattr(commands, 'find'):            # ancient hg
            findcmd = commands.find
        else:
            raise RuntimeError("unable to locate mercurial's 'findcmd()'")
        return dict([(f[1].replace('-', '_'), f[2]) for f in findcmd(cmd)[1][1]])

    def _hgCommand(self, cmd, *args, **opts):
        import os

        allopts = self._defaultOpts(cmd)
        allopts.update(opts)
        cmd = getattr(commands, cmd)
        cwd = os.getcwd()
        os.chdir(self.repository.basedir)
        try:
            cmd(self._ui, self._hg, *args, **allopts)
        finally:
            os.chdir(cwd)

    def _removePathnames(self, names):
        """Remove a sequence of entries"""

        from os.path import join

        repo = self._getRepo()

        self.log.info('Removing %s...', ', '.join(names))
        for name in names:
            files = self._walk(name)
            # We can't use isdir because the source has already
            # removed the entry, so we do a dirstate lookup.
            if files:
                for f in self._walk(name):
                    repo.remove([join(name, f)], unlink=True)
            else:
                repo.remove([name], unlink=True)

    def _renamePathname(self, oldname, newname):
        """Rename an entry"""

        from os.path import join, isdir, normpath

        repo = self._getRepo()

        self.log.info('Renaming %r to %r...', oldname, newname)
        # Check both names, because maybe we are operating in
        # disjunct dirs, and the target may be renamed to a
        # temporary name
        if (isdir(join(self.repository.basedir, normpath(oldname)))
            or isdir(join(self.repository.basedir, normpath(newname)))):
            # Given lack of support for directories in current HG,
            # loop over all files under the old directory and
            # do a copy on them.
            for f in self._walk(oldname):
                oldpath = join(oldname, f)
                repo.copy(oldpath, join(newname, f))
                repo.remove([oldpath], unlink=True)
        else:
            repo.copy(oldname, newname)
            repo.remove([oldname], unlink=True)

    def _prepareTargetRepository(self):
        """
        Create the base directory if it doesn't exist, and the
        repository as well in the new working directory.
        """

        from os.path import join, exists, realpath

        self._getUI()

        if exists(join(self.repository.basedir, self.repository.METADIR)):
            create = 0
        else:
            create = 1
            self.log.info('Initializing new repository in %r...', self.repository.basedir)
        self._hg = hg.repository(ui=self._ui, path=realpath(self.repository.basedir),
                                 create=create)

    def _prepareWorkingDirectory(self, source_repo):
        """
        Create the .hgignore.
        """

        from os.path import join
        from re import escape
        from vcpx.dualwd import IGNORED_METADIRS

        # Create the .hgignore file, that contains a regexp per line
        # with all known VCs metadirs to be skipped.
        ignore = open(join(self.repository.basedir, '.hgignore'), 'w')
        ignore.write('\n'.join(['(^|/)%s($|/)' % escape(md)
                                for md in IGNORED_METADIRS]))
        ignore.write('\n')
        if self.logfile.startswith(self.repository.basedir):
            ignore.write('^')
            ignore.write(self.logfile[len(self.repository.basedir)+1:])
            ignore.write('$\n')
        if self.state_file.filename.startswith(self.repository.basedir):
            sfrelname = self.state_file.filename[len(self.repository.basedir)+1:]
            ignore.write('^')
            ignore.write(sfrelname)
            ignore.write('$\n')
            ignore.write('^')
            ignore.write(sfrelname+'.old')
            ignore.write('$\n')
            ignore.write('^')
            ignore.write(sfrelname+'.journal')
            ignore.write('$\n')
        ignore.close()
        self._hg.add(['.hgignore'])
        self._hgCommand('commit', '.hgignore',
                        message = 'Tailor preparing to convert repo by adding .hgignore')

    def _initializeWorkingDir(self):
        self._hgCommand('add')

    def _walk(self, subdir):
        """
        Returns the files mercurial knows about under subdir, relative
        to subdir.
        """
        from os.path import join, split

        files = []
        for src, path in self._getRepo().dirstate.walk([subdir]):
            # If subdir is a plain file, just return
            if path == subdir:
                return None
            (hd, tl) = split(path)
            while hd != subdir and hd != '':
                hd, nt = split(hd)
                tl = join(nt, tl)
            files.append(tl)
        return files
