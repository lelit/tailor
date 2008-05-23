#
# Copyright (C) 2008 Walter Franzini
#

"""
This module contains the target specific bits of the Aegis backend.
"""

__docformat__ = 'reStructuredText'

import os
import os.path
import re
from tempfile import mkstemp, NamedTemporaryFile

from vcpx.shwrap import ExternalCommand, PIPE, STDOUT
from vcpx.source import ChangesetApplicationFailure
from vcpx.target import SynchronizableTargetWorkingDir
from vcpx.tzinfo import UTC


MOTD = """\
Tailorized equivalent of
%s
"""


__docformat__ = 'reStructuredText'

import re

from vcpx.shwrap import ExternalCommand, PIPE, STDOUT
from vcpx.source import ChangesetApplicationFailure
from vcpx.target import SynchronizableTargetWorkingDir
from vcpx.tzinfo import UTC


MOTD = """\
Tailorized equivalent of
%s
"""


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
        # Add the very first change to the repository.
        # This change set add aegis configuration file to the project.
        #

        #
        # Aegis refuse to use an already existing directory as the
        # development directory of a change.
        #
        if os.path.exists(self.repository.basedir):
            os.rmdir(self.repository.basedir)

        self.change_number = self.__new_change("setup aegis",
                                               "Prepare aegis configuration")
        self.__develop_begin()
        self.__new_file("aegis.conf", "config")
        self.__config_file(self.repository.basedir, "aegis.conf")
        self.__develop_end()
        self.__integrate_begin()
        self.__integrate_pass()

    def _prepareToReplayChangeset(self, changeset):
        """
        Runs aegis -New_Change -dir target.basedir
        """
        self.change_number = self.__new_change(changeset.revision, "bla bla")
        self.__develop_begin()
        #
        # This function MUST return
        #
        return True

    def _prepareWorkingDirectory(self, source_repo):
        #
        # Receive the first changeset from the source repository.
        #
        self.change_number = self.__new_change("bla2", "bla2 bla2")
        self.__develop_begin()
        return True

    def _addPathnames(self, names):
        for name in names:
            self.__new_file(name)

    def _editPathnames(self, names):
        for name in names:
            self.__copy_file(name)

    def _removePathnames(self, named):
        for name in names:
            self.__remove_file(name)

    def _renamePathname(self, oldname, newname):
        self.__move_file(oldname, newname)

    #
    # The following methods wraps change's related aegis commands.
    #
    def __new_change(self, title, description):
        change_attr = NamedTemporaryFile()
        change_attr.write("brief_description = \"%s\";\n" % title)
        change_attr.write("description = \"%s\";" % description)
        change_attr.write("cause = external_improvement;\n")
        change_attr.flush()
        change_number_file = mkstemp()[1]
        cmd = self.repository.command("-new_change",
                                      "-project", self.repository.module,
                                      "-file", change_attr.name,
                                      "-output", change_number_file)
        new_change = ExternalCommand(cwd="/tmp", command=cmd)
        output = new_change.execute(stdout = PIPE, stderr = STDOUT)[0]
        if new_change.exit_status > 0:
            raise ChangesetApplicationFailure(
                "%s returned status %d, saying: %s" % (str(new_change),
                                                       new_change.exit_status,
                                                       output.read()))
        f = open(change_number_file, "r")
        change_number = f.read()
        f.close()
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
        if integrate_begin > 0:
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
        if finish > 0:
            raise ChangesetApplicationFailure(
                "%s returned status %d, saying: %s" %
                (str(finish), finish.exit_status, output.read()))

    def __change_attribute(self):
        pass

    #
    # File's related change commands.
    #
    def __new_file(self, file_names, usage = None):
        if usage == "config":
            cmd = self.repository.command("-new_file", "-keep", "-config",
                                          "-project", self.repository.module,
                                          "-change", self.change_number)
        else:
            cmd = self.repository.command("-new_file", "-keep",
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
        self.log.info("AEGIS: aegis -move -project %s -change %s "
                      "-base-relative %s %s", self.repository.module,
                      self.change_number, old_name, new_name)
        pass

    def __remove_file(self, file_name):
        self.log.info("AEGIS: aegis -remove -project %s -change %s "
                      "-base-relative %s", self.repository.module,
                      self.change_number, file_name)
        pass

    def __config_file(self, dir, name):
        c = open(os.path.join(dir, name), "wb", 0777)
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
merge_command = "(diff3 -e $i $orig $mr | sed -e '/^w$$/d' -e '/^q$$/d'; \
	echo '1,$$p' ) | ed - $i > $out";
patch_diff_command = "set +e; $diff -C0 -L $index -L $index $orig $i > $out; \
test $$? -le 1";
""")
        c.close()

