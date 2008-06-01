# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Aegis details
# :Creato:   sab 24 mag 2008 15:44:00 CEST
# :Autore:   Walter Franzini <walter.franzini@gmail.com>
# :Licenza:  GNU General Public License
#

"""
This module contains the target specific bits of the Aegis backend.
"""

__docformat__ = 'reStructuredText'

import os
import os.path
import re
import shutil

from vcpx.changes import ChangesetEntry
from vcpx.shwrap import ExternalCommand, ReopenableNamedTemporaryFile, PIPE, STDOUT
from vcpx.source import ChangesetApplicationFailure
from vcpx.target import SynchronizableTargetWorkingDir


class AegisTargetWorkingDir(SynchronizableTargetWorkingDir):
    """
    A target working directory under ``Aegis``.
    """

    change_number = "not-a-number"

    def _commit(self, date, author, patchname, changelog=None, entries=None,
                tags = [], isinitialcommit = False):
        """
        Commit the changeset.
        """

        #
        # The invocation for the initialcommit does not receive entries.
        #
        if isinitialcommit:
            self.__new_file("aegis.conf", "config")
            self.__config_file(self.repository.basedir, "aegis.conf")
        elif not entries:
            #
            # Return successfully even if the changeset does not
            # contain entries just in case it's a tag changeset.
            #
            return True


        change_attribute_file = \
            self.__change_attribute_file(brief_description=patchname,
                                         description=changelog)
        self.__change_attribute(change_attribute_file.name)
        self.__develop_end()
        #
        # If the change cannot be closed, e.g. because a file is
        # modified in a change not yet integrated, then we should stop here.
        #
        # return False
        #
        # Next step only if develop_end => awaiting_integration
        #
        self.__integrate_begin()
        self.__finish()

    def _prepareTargetRepository(self):
        #
        # Aegis refuse to use an already existing directory as the
        # development directory of a change.
        #
        if os.path.exists(self.repository.basedir):
            shutil.rmtree(self.repository.basedir)

    def _prepareToReplayChangeset(self, changeset):
        """
        Runs aegis -New_Change -dir target.basedir
        """

        self._prepareTargetRepository()
        self.change_number = self.__new_change(changeset.revision)
        self.__develop_begin()
        #
        # This function MUST return
        #
        return True

    def _adaptChangeset(self, changeset):
        project_files = self.repository.project_file_list_get()
        if not project_files:
            return SynchronizableTargetWorkingDir._adaptChangeset(self, changeset)

        from copy import deepcopy
        adapted = deepcopy(changeset)

        #
        # adapt the entries:
        # * delete directory entries
        # * delete entries with action_kind REMOVE not in the repository (DEL => )
        # * change to ADD a rename of a file non in the repository (REN => ADD)
        # * remove from the changeset entries whith 2 operation (REN + UPD => REN);
        # * change the ADD action_kind for files already in the repository (ADD => UPD);
        # * change the UPD action_kind for files *non* in the repository (UPD => ADD);
        #
        for e in adapted.entries[:]:
            if e.is_directory:
                adapted.entries.remove(e)
                continue
            if e.action_kind == e.DELETED and not project_files.count(e.name):
                self.log.info("remove delete entry %s", e.name)
                adapted.entries.remove(e)

        renamed_file = []
        for e in adapted.entries:
            if e.action_kind == e.RENAMED:
                renamed_file.append(e.name)

        for e in adapted.entries[:]:
            if renamed_file.count(e.name) and e.action_kind != e.RENAMED:
                adapted.entries.remove(e)
            if e.action_kind == e.RENAMED and not project_files.count(e.old_name):
                e.action_kind = e.ADDED
                e.old_name = None
            if e.action_kind == e.ADDED and project_files.count(e.name):
                e.action_kind = ChangesetEntry.UPDATED
            elif e.action_kind == e.UPDATED and not project_files.count(e.name):
                e.action_kind = e.ADDED

        #
        # Returns even if the changeset does not contain entries to
        # give the opportunity to still register tags.
        #
        return SynchronizableTargetWorkingDir._adaptChangeset(self, adapted)

    def _initializeWorkingDir(self):
        #
        # This method is called only by importFirstRevision
        #
        self.__new_file('.')

    def _prepareWorkingDirectory(self, source_repo):
        #
        # Receive the first changeset from the source repository.
        #
        self.change_number = self.__new_change()
        self.__develop_begin()
        return True

    def _tag(self, tag, author, date):
        self.__delta_name(tag)

    def _addSubtree(self, subdir):
        #
        # Aegis new_file command is recursive, there is no need to
        # walk the directory tree.
        #
        pass

    def _addEntries(self, entries):
        for e in entries:
            self.__new_file(e.name)

    def _addPathnames(self, names):
        for name in names:
            self.__new_file(name)

    def _editPathnames(self, names):
        for name in names:
            self.__copy_file(name)

    def _removeEntries(self, entries):
        for e in entries:
            self.__remove_file(e.name)

    def _removePathnames(self, names):
        for name in names:
            self.__remove_file(name)

    def _renameEntries(self, entries):
        for e in entries:
            self.__move_file(e.old_name, e.name)

    def _renamePathname(self, oldname, newname):
        self.__move_file(oldname, newname)

    #
    # The following methods wraps change's related aegis commands.
    #
    def __new_change(self, title = "none", description = "none"):
        change_attr_file = \
            self.__change_attribute_file(brief_description = title,
                                         description = description)
        change_number_file = ReopenableNamedTemporaryFile('aegis', 'tailor')
        cmd = self.repository.command("-new_change",
                                      "-project", self.repository.module,
                                      "-file", change_attr_file.name,
                                      "-output", change_number_file.name)
        new_change = ExternalCommand(cwd="/tmp", command=cmd)
        output = new_change.execute(stdout = PIPE, stderr = STDOUT)[0]
        if new_change.exit_status > 0:
            raise ChangesetApplicationFailure(
                "%s returned status %d, saying: %s" % (str(new_change),
                                                       new_change.exit_status,
                                                       output.read()))
        fd = open(change_number_file.name, "rb")
        change_number = fd.read()
        fd.close()
        return change_number.strip()

    def __develop_begin(self):
        cmd = self.repository.command("-develop_begin",
                                      "-project", self.repository.module,
                                      "-change", self.change_number,
                                      "-directory", self.repository.basedir)
        develop_begin = ExternalCommand(cwd="/tmp", command=cmd)
        output = develop_begin.execute(stdout = PIPE, stderr = STDOUT)[0]
        if develop_begin.exit_status > 0:
            raise ChangesetApplicationFailure(
                "%s returned status %d, saying: %s" %
                (str(develop_begin), develop_begin.exit_status, output.read()))
        self.log.info(output.read())

    def __develop_end(self):
        self.__finish()

    def __integrate_begin(self):
        cmd = self.repository.command("-integrate_begin",
                                      "-project", self.repository.module,
                                      "-change", self.change_number)
        integrate_begin = ExternalCommand(cwd="/tmp", command=cmd)
        output = integrate_begin.execute(stdout = PIPE, stderr = STDOUT)[0]
        if integrate_begin.exit_status > 0:
            raise ChangesetApplicationFailure(
                "%s returned status %d, saying: %s" %
                (str(integrate_begin), integrate_begin.exit_status,
                 output.read()))

    def __integrate_pass(self):
        self.__finish()

    def __finish(self):
        cmd = self.repository.command("-finish",
                                      "-project", self.repository.module,
                                      "-change", self.change_number)
        finish = ExternalCommand(cwd="/tmp", command=cmd)
        output = finish.execute(stdout = PIPE, stderr = STDOUT)[0]
        if finish.exit_status > 0:
            raise ChangesetApplicationFailure(
                "%s returned status %d, saying: %s" %
                (str(finish), finish.exit_status, output.read()))

    def __change_attribute(self, file):
        cmd = self.repository.command ("-change_attr",
                                       "-project", self.repository.module,
                                       "-change", self.change_number)
        change_attr = ExternalCommand (cwd="/tmp", command=cmd)
        output = change_attr.execute ("-file", file, stdout = PIPE, stderr = STDOUT)[0]
        if change_attr.exit_status > 0:
            raise ChangesetApplicationFailure(
                "%s returned status %d, saying: %s" %
                (str(change_attr), change_attr.exit_status, output.read()))

    def __delta_name (self, delta):
        cmd = self.repository.command ("-delta_name",
                                       "-project", self.repository.module)
        delta_name = ExternalCommand (cwd="/tmp", command=cmd)
        output = delta_name.execute (delta, stdout = PIPE, stderr = STDOUT)[0]
        if delta_name.exit_status > 0:
            raise ChangesetApplicationFailure(
                "%s returned status %d, saying: %s" %
                (str(delta_name), delta_name.exit_status, output.read()))

    #
    # File's related methods.
    #
    def __new_file(self, file_names, usage = None):
        #
        # Tailor try to add also the aegis own log file and it's forbidden.
        #
        if file_names == "./aegis.log":
            return
        if usage == "config":
            cmd = self.repository.command("-new_file", "-keep", "-config",
                                          "-not-logging",
                                          "-project", self.repository.module,
                                          "-change", self.change_number)
        else:
            cmd = self.repository.command("-new_file", "-keep", "-not-logging",
                                          "-project", self.repository.module,
                                          "-change", self.change_number)
        new_file = ExternalCommand(cwd=self.repository.basedir,
                                   command=cmd)
        output = new_file.execute(file_names, stdout = PIPE, stderr = STDOUT)[0]
        if new_file.exit_status > 0:
            raise ChangesetApplicationFailure(
                "%s returned status %d, saying: %s" %
                (str(new_file), new_file.exit_status, output.read()))


    def __copy_file(self, file_names):
        cmd = self.repository.command("-copy", "-keep",
                                      "-not-logging",
                                      "-project", self.repository.module,
                                      "-change", self.change_number)
        copy_file = ExternalCommand(cwd=self.repository.basedir,
                                    command=cmd)
        output = copy_file.execute(file_names, stdout = PIPE, stderr = STDOUT)[0]
        if copy_file.exit_status > 0:
            raise ChangesetApplicationFailure(
                "%s returned status %d, saying: %s" %
                (str(copy_file), copy_file.exit_status, output.read()))

    def __move_file(self, old_name, new_name):
        #
        # The aegis command to rename files does not have the -keep
        # option to preserve the content of the file, do it manually.
        #
        fp = open(os.path.join(self.repository.basedir, new_name), 'rb')
        content = fp.read()
        fp.close()
        cmd = self.repository.command("-move",
                                      "-not-logging",
                                      "-project", self.repository.module,
                                      "-change", self.change_number)
        move_file = ExternalCommand(cwd=self.repository.basedir,
                                    command=cmd)
        output = move_file.execute(old_name, new_name, stdout = PIPE, stderr = STDOUT)[0]
        if move_file.exit_status > 0:
            raise ChangesetApplicationFailure(
                "%s returned status %d, saying: %s" %
                (str(move_file), move_file.exit_status, output.read()))

        #
        # Restore the previously saved content of the renamed file.
        #
        fp = open(os.path.join(self.repository.basedir, new_name), 'wb')
        fp.write(content)
        fp.close()

    def __remove_file(self, file_name):
        cmd = self.repository.command("-remove",
                                      "-not-logging",
                                      "-project", self.repository.module,
                                      "-change", self.change_number)
        remove_file = ExternalCommand(cwd=self.repository.basedir,
                                      command=cmd)
        output = remove_file.execute(file_name, stdout = PIPE, stderr = STDOUT)[0]
        if remove_file.exit_status > 0:
            raise ChangesetApplicationFailure(
                "%s returned status %d, saying: %s" %
                (str(remove_file), remove_file.exit_status, output.read()))

    def __change_attribute_file(self, *args, **kwargs):
        """
        Create a temporary file to modify change's attributes.
        """
        if kwargs['brief_description']:
            brief_description = \
                self.repository.normalize(kwargs['brief_description'])
        else:
            brief_description = 'none'
        if kwargs['description']:
            description = \
                self.repository.normalize(kwargs['description'])
        else:
            description = "none"
        attribute_file = ReopenableNamedTemporaryFile('aegis', 'tailor')
        fd = open(attribute_file.name, 'wb')
        fd.write("""
            brief_description = "%s";
            description = "%s";
            cause = external_improvement;
            test_exempt = true;
            test_baseline_exempt = true;
            regression_test_exempt = true;
            """
            % (brief_description, description))
        fd.close()
        return attribute_file

    def __config_file(self, dir, name):
        """
        Prepare the basic configuration to make aegis work:
        * define a successfull build command (exit 0)
        * define the history command
        * define the merge commands
        """
        c = open(os.path.join(dir, name), "wb", 0644)
        c.write("""
build_command = "exit 0";
link_integration_directory = true;

history_get_command = "aesvt -check-out -edit ${quote $edit} "
    "-history ${quote $history} -f ${quote $output}";
history_put_command = "aesvt -check-in -history ${quote $history} "
    "-f ${quote $input}";
history_query_command = "aesvt -query -history ${quote $history}";
history_content_limitation = binary_capable;

diff_command = "set +e; $diff $orig $i > $out; test $$? -le 1";
merge_command =
"(diff3 -e $i $orig $mr | sed -e '/^w$$/d' -e '/^q$$/d'; echo '1,$$p') "
"| ed - $i > $out";
patch_diff_command =
"set +e; $diff -C0 -L $index -L $index $orig $i > $out; test $$? -le 1";

shell_safe_filenames = false;
""")
        c.close()
