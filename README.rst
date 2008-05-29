.. Hey! This is reStructuredText, where "*this*" notation means an
.. italic "this" and similar oddities. See the notes at the end of
.. this file for details.

Tailor 1.0
##########

.. contents::

About
=====

Tailor is a tool to migrate changesets between Aegis_, ArX_, Baz_,
`Bazaar`_, CVS_, Codeville_, Darcs_, Git_, Mercurial_, Monotone_,
Perforce_, Subversion_ and Tla_ [#]_ repositories.

This script makes it easier to keep the upstream changes merged in
a branch of a product, storing needed information such as the upstream
URI and revision in special properties on the branched directory.

The following ascii-art illustrates the usual scenario::

                           +------------+            +------------+
  +--------------+         | Immutable  |            | Working    |
  | Upstream CVS |-------->| darcs      |----------->| darcs      |
  | repository   | tailor  | repository | darcs pull | repository |
  +--------------+         +------------+            +------------+
                                                           |^
                                                           ||
                                                           ||
                                                           v|
                                                          User

Ideally you should be able to swap and replace "CVS server" and "darcs
repository" with any combination of the supported systems.

It's still lacks the ability of doing a `two way sync`_.

.. [#] Aegis, ArX and Codeville systems may be used only as the `target`
       backend, since the `source` support isn't coded yet.
       Contributions on these backends will be very appreciated,
       since I do not use them enough to figure out the best way to
       get pending changes and build tailor ChangeSets out of them.

       To the opposite, Baz (1.0, not Bazaar), Perforce and Tla
       are supported only as source systems.

.. _aegis: http://aegis.sourceforge.net/
.. _arx: http://www.nongnu.org/arx/
.. _baz: http://bazaar-vcs.org/Baz1x
.. _bazaar: http://bazaar-vcs.org/
.. _codeville: http://www.codeville.org/
.. _cvs: http://www.nongnu.org/cvs/
.. _darcs: http://www.darcs.net/
.. _git: http://git.or.cz/
.. _mercurial: http://www.selenic.com/mercurial/
.. _monotone: http://www.monotone.ca/
.. _perforce: http://www.perforce.com/
.. _subversion: http://subversion.tigris.org/
.. _tla: http://www.gnuarch.org/arch/index.html
.. _two way sync: http://progetti.arstecnica.it/tailor/wiki/TwoWaySync


Installation
============

tailor is written in Python, and thus Python must be installed on
your system to use it.  It has been successfully used with Python 2.3,
2.4 and 2.5.

Since it relies on external tools to do the real work such as `cvs`,
`darcs` [#]_ and `svn`, they need to be installed as well, although only
those you will actually use.

Make tailor executable::

 $ chmod +x tailor

You can either run tailor where it is currently located, or move it
along with the vcpx directory to a location in your PATH.

There's even a standard setup.py that you may use to install the
script using Python's conventional distutils.

.. [#] Darcs 1.0.2 is too old, 1.0.3 is good, 1.0.4 (the fourth
       release candidate is under final testing) is recommended since
       it's faster in most operations!


Testing
=======

Tailor has more than 50 unit and operational tests, that you can
run with the following command line::

 $ tailor test -v

Since some tests take very long to complete, in particular the
operational tests, you may prefer the execution of a single suite::

 $ tailor test -v Darcs

or even a single test within a suite::

 $ tailor test StateFile.testJournal

To obtain a list of the test, use ``--list`` option.  As usual with::

 $ tailor test --help

you will get some more details.

More recently, a suite of functional tests was added, in the directory
``./test-scripts``: these are simple shell scripts that basically
build a source repository, create a configuration file and run tailor,
checking the result. You can execute them with::

 $ sh test-svn2svn-simple.sh

or::

 $ sh run-all-test.sh


Operation
=========

tailor needs now a configuration file that collects the various bits
of information it needs to do its job.

The simplest way of starting out a new configuration is by omitting
the ``--configfile`` command line option, and specifying the other as
needed plus ``--verbose``: in this situation, tailor will print out an
equivalent configuration that you can redirect to a file, that you
later will pass as ``--configfile`` (or simply ``-c``).


Examples
--------

1. Bootstrap a new tailored project, starting at upstream revision 10

   a. First create a config file::

       $ tailor --verbose -s svn -R http://svn.server/path/to/svnrepo \
                --module /Product/trunk -r 10 --subdir Product \
                ~/darcs/MyProduct > myproject.tailor

   b. Modify it as you like (mostly adjusting root-directories and the
      like)::

       $ emacs myproject.tailor

   c. Run tailor on it::

       $ tailor --configfile myproject.tailor

2. Bootstrap a new product, fetching its whole CVS repository and
   storing under SVN

   a. First create a config file::

       $ tailor --verbose --source-kind cvs --target-kind svn \
                --repository :pserver:cvs.zope.org:/cvs-repository \
                --module CMF/CMFCore --revision INITIAL \
                --target-repository file:///some/where/svnrepo \
                --target-module / cmfcore > cmfcore.tailor

   b. Modify it as you like (mostly adjusting root-directories and the
      like)::

       $ emacs cmfcore.tailor

   .. note:: By default, tailor uses "." as ``subdir``, to mean that
             it will extract upstream source directly inside the
             ``root-directory``.

             This is known to cause problems with CVS as source, with
             which you could see some wierd error like

             ::

               $ cvs -q -d ...:/cvsroot/mymodule checkout -d . ... mymodule
               cvs checkout: existing repository /cvsroot/mymodule does not match /cvsroot/mymodule/mymodule
               cvs checkout: ignoring module mymodule

             When this is the case, the culprit may be a CVS
             shortcoming not being able to handle ``-d .`` in the
             right way.  Specify a different ``subdir`` option to
             avoid the problem.

   c. Run tailor on it once, to bootstrap the project::

       $ tailor -D -v -c cmfcore.tailor

      If the target repository is on the local filesystem (ie, it
      starts with ``file:///``) and it does not exist, tailor
      creates a new empty Subversion repository at the specified
      location.

   .. note:: Before step d) below, you may want to install an
             appropriate hook in the repository to enable the
             propset command to operate on unversioned properties,
             as described in the `svn manual`__. Then you can
             specify '--use-propset' option, and tailor will
             put the original author and timestamp in the proper
             svn metadata instead of appending them to the changelog.

             Other than the annoying repository manual intervention,
             this thread__ and this other__ explain why using
             ``-r{DATE}`` may produce strange results with this setup.

   d. Run tailor again and again, to sync up with latest changes::

       $ tailor -v --configfile cmfcore.tailor

__ http://svnbook.red-bean.com/en/1.0/ch05s02.html#svn-ch-5-sect-2.1
__ http://svn.haxx.se/users/archive-2005-07/0605.shtml
__ http://svn.haxx.se/users/archive-2005-03/0596.shtml


3. Given the configuration file shown below in `Config file format`_,
   the following command::

    $ tailor --configfile example.tailor

   is equivalent to this one::

    $ tailor --configfile example.tailor tailor

   in that they operate respectively on the default project(s) or
   the ones specified on the command line (and in this case there
   is just a single default project, tailor).

   This one instead::

    $ tailor -c example.tailor tailor tailor-reverse

   operates on both projects.


CVS start-revision
------------------

With CVS, you can specify a particular *point in time* specifying
a `start-revision` with a timestamp like ``2001-12-25 23:26:48 UTC``.

To specify also a particular `branch`, prepend it before the
timestamp, as in ``unstable-branch 2001-12-25 23:26:48 UTC``.

To migrate the whole history of a specific `branch`, use something
like ``somebranch INITIAL``.


Resolving conflicts
===================

Should one of the replayed changes generate any conflict, tailor
will prompt the user to correct them. This is done after the upstream
patch has been applied and before the final commit on the target
system, so that manually tweaking the conflict can produce a clean
patch.


Shortcomings
============

Tailor currently suffers of the following reported problems:

a) It does not handle "empty" CVS checkouts, in other words you cannot
   bootstrap a project that has nothing in its CVS upstream
   repository, or from a point in time where this condition was true.

b) It's completely unsupported under Windows, evenif it now uses
   2.4's subprocess_ that seems able to hide Windows crazyness...

c) ArX and Codeville are (currently) only supported as *target*;
   Baz and Tla only as *source*.

d) Specifying ``--subdir .`` may not work, in particular when dealing
   with remote CVS repositories (it does when the CVS repository is
   on local machine).

This list will always be incomplete, but I'll do my best to keep it
short :-)

.. _subprocess: http://www.lysator.liu.se/~astrand/popen5/


Config file format
==================

When your project is composed by multiple upstream modules, it is
easier to collect such information in a single file. This is done by
specifying the `--configfile` option with a file name as argument. In
this case, tailor will read the above information from a standard
Python ConfigParser file.

For example::

    [DEFAULT]
    verbose = True
    projects = tailor

    [tailor]
    root-directory = /tmp/n9
    source = darcs:tailor
    target = svn:tailor
    state-file = tailor.state

    [tailor-reverse]
    root-directory = /tmp/n9
    source = svn:tailor
    target = darcs:tailor
    state-file = reverse.state

    [svn:tailor]
    repository = file:///tmp/testtai
    module = /project1
    subdir = svnside

    [darcs:tailor]
    repository = ~/WiP/cvsync
    subdir = darcside

The configuration may hold one or more `projects`_ and two or more
`repositories`_: project names do not contains colons ":",
repository names must and the first part of the name before the
colon specify the kind of the repository.  So, the above example
contains two projects, one that goes from `darcs` to `subversion`, the
other in the opposite direction.

The ``[DEFAULT]`` section contains the default values, that will be
used when a specific setting is missing from the particular section.

You can specify on which project tailor should operate by
giving its name on the command line, even more than one. When not
explicitly given, tailor will look at ``projects`` in the
``[DEFAULT]`` section, and if its missing it will loop over all
projects in the configuration.

The following simpler config just go in one direction, for a single
project, so no need neither for ``[DEFAULT].projects`` nor command
line arguments. Also, notice the usage of the repository short cut:
the ``source`` and ``target`` will be implicitly loaded from
`cvs:pxlib` and `hg:pxlib` respectively::

    [pxlib]
    source = cvs:
    target = hg:
    root-directory = ~/mypxlib
    start-revision = INITIAL
    subdir = pxlib

    [cvs:pxlib]
    repository = :pserver:anonymous@cvs.sf.net:/cvsroot/pxlib
    module = pxlib

    [hg:pxlib]

This will use a single directory, ``pxlib`` to contain both the source
and the target system. If you prefer keeping them separated, you just
need to specify a different directory for each repository [#]_, as in::

    [pxlib]
    source = cvs:pxlib
    target = hg:pxlib
    root-directory = ~/mypxlib
    start-revision = INITIAL

    [cvs:pxlib]
    repository = :pserver:anonymous@cvs.sf.net:/cvsroot/pxlib
    module = pxlib
    subdir = original
    delay-before-apply = 10

    [hg:pxlib]
    subdir = migrated

This will extract upstream CVS sources into ``~/mypxlib/original``,
and create a new Mercurial repository in ``~/mypxlib/migrated``.

The following example shows the syntax of Baz sources::

    [project]
    target = hg:target
    start-revision = base-0
    root-directory = /tmp/calife
    state-file = hidden
    source = baz:source

    [baz:source]
    module = calife--pam--3.0
    repository = roberto@keltia.net--2003-depot
    subdir = tla

    [hg:target]
    repository = /tmp/HG/calife-pam
    subdir = hg

Note the usage of ``hidden`` for the state file name: given the
importance of this file, that at the same time is of no interest by
the user, this will store that information `inside` the same directory
used by the target repository for its metadata, with the name
``tailor.state``.  In this particular example, it will end up as
``/tmp/calife/hg/.hg/tailor.state``.

Last, a complete example used to migrate the whole Monotone_ source
repository under Subversion_::

    [DEFAULT]
    #debug = True
    #verbose = True
    start-revision = INITIAL
    root-directory = /tmp/rootdir-Monotone
    source = monotone:
    target = svn:
    source-repository = /home/user/Monotone/monotone-database.mtn
    target-repository = file:///tmp/svn-repository
    use-propset = True

    # Projects
    [net.venge.monotone.cvssync]

    [net.venge.monotone.cvssync.attrs]

    [net.venge.monotone.de]

    [net.venge.monotone.svn_import]

    [net.venge.monotone]


    # Sources
    [monotone:net.venge.monotone.cvssync]
    module = net.venge.monotone.cvssync
    subdir = mtnside-net.venge.monotone.cvssync

    [monotone:net.venge.monotone.cvssync.attrs]
    module = net.venge.monotone.cvssync.attrs
    subdir = mtnside-net.venge.monotone.cvssync.attrs

    [monotone:net.venge.monotone.de]
    module = net.venge.monotone.de
    subdir = mtnside-net.venge.monotone.de

    [monotone:net.venge.monotone.svn_import]
    module = net.venge.monotone.svn_import
    subdir = mtnside-net.venge.monotone.svn_import

    [monotone:net.venge.monotone]
    module = net.venge.monotone
    subdir = mtnside-net.venge.monotone


    # Targets
    [svn:net.venge.monotone.cvssync]
    module = branches/net.venge.monotone.cvssync
    subdir = svnside-net.venge.monotone.cvssync

    [svn:net.venge.monotone.cvssync.attrs]
    module = branches/net.venge.monotone.cvssync.attrs
    subdir = svnside-net.venge.monotone.cvssync.attrs

    [svn:net.venge.monotone.de]
    module = branches/net.venge.monotone.de
    subdir = svnside-net.venge.monotone.de

    [svn:net.venge.monotone.svn_import]
    module = branches/net.venge.monotone.svn_import
    subdir = svnside-net.venge.monotone.svn_import

    [svn:net.venge.monotone]
    module = trunk
    subdir = svnside-net.venge.monotone

.. [#] NB: when the source and the target repositories specify
       different directories with the ``subdir`` option, tailor
       uses ``rsync`` to keep them in sync, so that tool needs
       to be installed.


Configuration sections
----------------------

Default
~~~~~~~

The ``[DEFAULT]`` section in the configuration file may set the
default value for any of the recognized options: when a value is
missing from a specific section it is looked up in this section.

One particular option, ``projects``, is meaningful only in the
``[DEFAULT]`` section: it's a comma separated list of project names,
the one that will be operated on by tailor when no project is
specified on the command line.  When the there are no ``projects``
setting nor any on the command line, tailor activates all configured
projects, in order of appearance in the config file.


Projects
~~~~~~~~

A project is identified by a section whose name does not contain any
colon (":") character, and configured with the following values:

.. note:: If a particular option is missing from the project section,
          its value is obtained looking up the same option in the
          ``[DEFAULT]`` section.

root-directory : string
  This is where all the fun will happen: this directory will contain
  the source and the target working copy, and usually the state and
  the log file. It supports the conventional `~user` to indicate user's
  home directory and defaults to the current working directory.

subdir : string
  This is the subdirectory, relative to the `root-directory`, where
  tailor will extract the source working copy. It may be '.' for some
  backend kinds. The source and target backends will use this value
  if they don't explicitly override it.

state-file : string
  Name of the state file needed to store tailor last activity. When
  this is set to ``hidden``, the state file will be named
  ``tailor.state``, possibly under the target's ``METADIR``.

source : string
  The source repository: a repository name is something like
  "darcs:somename", that will be loaded from the homonymous section
  in the configuration. As a short cut, the "somename" part may be
  omitted: in that case, the project name will be appended to the
  specified prefix.

target : string
  The counterpart of `source`, the repository that will receive the
  changes coming from there.

Non mandatory options:

verbose : bool
  Print the commands as they are executed.

debug : bool
  Print also their output.

before-commit : tuple
  This is a function name, or a sequence of function names enclosed
  by brackets, that will be executed on each changeset just before
  it get replayed on the target system: this may be used to perform
  any kind of alteration on the content of the changeset, or to skip
  some of them.

after-commit : tuple
  This is a function name, or a sequence of function names enclosed
  by brackets, that will be executed on each changeset just after
  the commit on the target system: this may be used for example to
  create a tag.

subdir : string
  The name of the subdirectory, under ``root-directory``, that will
  contain the source and target repositories/working directories.

start-revision : string
  This identifies from when tailor should start the migration. It can
  be either ``INITIAL``, to indicate the start of the history, or
  ``HEAD`` to indicate the current latest changeset, or a backend
  specific way of indicate a particular revision/tag in the history.
  See also `CVS start-revision`_ above.

patch-name-format : string
  Some backends have a distinct notion of `patch name` and `change
  log`, others just suggest a policy that the first line of the
  message is a summary, the rest if present is a more detailed
  description of the change.  With this option you can control the
  format of the name, or of the first line of the changelog.

  The prototype may contain ``%(keyword)s`` such as 'author', 'date',
  'revision', 'firstlogline', 'remaininglog' or 'project'.  It
  defaults to ``[%(project)s @ %(revision)s]`` [#]_.

  When you set it empty, as in

  ::

    [project]
    patch-name-format = ""

  tailor will keep the original changelog as is.

remove-first-log-line : bool
  Remove the first line of the upstream changelog. This is intended to
  go in pair with ``patch-name-format``, when using its 'firstlogline'
  variable to build the name of the patch.  The default is ``False``.

  A reasonable usage is::

    [DEFAULT]
    patch-name-format=[%(project)s @ %(revision)s]: %(firstlogline)s
    remove-first-log-line=True

refill-changelogs : bool
  Off by default, when active tailor reformats every changelog before
  committing on the target system.

.. [#] Modifying the changelog may have subtle consequences!
       Under darcs, for example, you may hit issue772_ by producing
       hash collisions, that happens when two distinct patches carry
       the same "unique" identifier (the hash is computed using
       *date*, *author*, *changelog* and other details, but **not**
       the actual content): the default setting, that adds a
       differentiating prefix, is safer from that point of view.

.. _issue772: http://bugs.darcs.net/issue772


Repositories
~~~~~~~~~~~~

All the section whose name contains at least one colon character
denote a repository.  A single repository may be shared by zero, one or
more projects.  The first part of the name up to the first colon
indicates the `kind` of the repository, one of ``aegis``, ``arx``,
``baz``, ``bzr``, ``cdv``, ``cvs``, ``darcs``, ``git``, ``hg``,
``monotone``, ``p4``,``svn`` and ``tla``.

.. note:: If a particular option is missing from the repository section,
          its value is obtained looking up the same option in the
          section of the project *currently* using the repository,
          falling back to the ``[DEFAULT]`` section.

Some options may be shared with others repositories, like in the
following example, where the common settings for the target monotone
repository are set just once::

  [DEFAULT]
  target-repository = /bigdisk/my-huge-repository.mtn
  target-keyid = test@example.com
  target-passphrase = lala
  source-repository = http://svn.someserver.com

  [productA]
  target = monotone:productA
  source = svn:sourceA

  [productB]
  target = monotone:productB
  source = darcs:sourceB

  [productC]
  target = monotone:productC
  source = svn:sourceC

  [productC_darcs]
  target = darcs:
  source = svn:sourceC

  ...

  [monotone:productA]
  module = every.thing.productA

  [monotone:productB]
  module = every.thing.productB

  [monotone:productC]
  module = every.thing.productC

  [svn:sourceA]
  module = /productA

  [darcs:sourceB]
  repository = http://some.server.com/darcs/productB

  [svn:sourceC]
  module = /productC

For some backends, for example for those that like ``darcs`` do not
make a distinction between `repository` and `working copy` and thus
the former may be assumed by ``root-directory`` (and possibly
``subdir``), the config section may be completely omitted, as done for
`productC_darcs` above.


Common options
%%%%%%%%%%%%%%

repository : string
  When a repository is used as a `source`, it must indicate its origin
  with ``repository``, and for some backends also a ``module``, but
  are not required when it's a target system, even if some backend may
  use the information to create the target repository (like ``svn``
  backend does).

subdir : string
  When the `source` and `target` repositories use different
  subdirectories, tailor uses ``rsync`` to copy the changes between
  the two after each applied changeset.  When the source repository
  basedir is a subdirectory of target basedir tailor prefixes all
  paths coming from upstream to match the relative position.

  This defaults to the project's setting.

command : string
  Backends based on external command line tool such as *svn* or
  *darcs* offers this option to impose a particular external binary to
  be used, as done below in the example about `disjunct working
  directories`_.

python-path : string
  For pythonique backends such as *bzr* and *hg* this indicates
  where the respective library is located.

encoding : string
  States the charset encoding the particular repository uses, and it's
  particularly important when it differs from local system setup, that
  you may inspect executing::

    python -m locale

encoding-errors-policy : string
  By default is *strict*, that means that Python will raise an
  exception on Unicode conversion errors. Valid options are *ignore*
  that simply skips offending glyphs and *replace* where unrecognized
  entities are replaced with a place holder.

delay-before-apply : integer
  Sometime the migration is fast enough to put the upstream server
  under an excessive load. When this is the case, you may specify
  ``delay-before-apply = 5``, that is the number of seconds tailor
  will wait before applying each changeset.

  It defaults to *None*, ie no delay at all.

post-commit-check : bool
  After each commit tailor will perform a check on the target working
  directory asserting there's no changes left. This is particularly
  useful when trying to debug source backends... at a little cost.

  *False* by default.

aegis
%%%%%

.. no specific option

Sample config fragment::

   [aegis:target]
   #
   # Set the aegis project as the tailor module, tailor will *not*
   # create the aegis project for you!
   #
   module = $AEGIS_PROJECT
   #
   # the subdir will be used as the working directory for aegis
   # changes, it *must* be different from the source:subdir.
   #
   subdir = aegisside


arx
%%%

.. no specific options

baz
%%%

.. no specific options

bzr
%%%

.. no specific options

cdv
%%%

.. no specific options

cvs
%%%

changeset-threshold : integer
  Maximum number of seconds allowed to separated commits to different
  files for them to be considered part of the same changeset.

  180 by default.

freeze-keywords : bool
  With this enabled (it is off by default) tailor will use ``-kk`` flag
  on `checkouts` and `updates` to turn off the keyword expansion. This
  may help minimizing the chance of spurious conflicts with later
  merges between different branches.

  *False* by default.

tag-entries : bool
  CVS and CVSPS repositories may turn off automatic tagging of
  entries, that tailor does by default to prevent manual interventions
  in the CVS working copy, using ``tag_entries = False``.

  *True* by default.

trim-module-components : integer
  When the checked out tree involves `CVS modules`__ on the server
  Tailor fails to build up the ChangeSets view from the ``cvs rlog``
  output, since in that case the paths that Tailor finds in the log
  refers to the real location of the entries *on the server*, and
  not, as usual, relatives to the root of the checked out tree. Of
  course, Tailor must be exact in correlating the information coming
  from the log and the actual checked out content in the filesystem,
  so in this case, by default it fails with an obscure message at
  bootstrap time.

  Given that most of the time it's simply a matter of a common prefix,
  this option offers the so called "far-from-perfect-poor-man-workaround"
  to the CVS/Tailor shortcoming, until a better solution arises.

  When you set this to an integer greater than zero, the parser will
  cut off that many components from the beginning of the pathnames it
  finds in the log.

  *0 (zero)* by default.

__ http://ximbiot.com/cvs/wiki/index.php?title=CVS--Concurrent_Versions_System_v1.12.12.1:_Reference_manual_for_Administrative_files#The_modules_file

cvsps
%%%%%

freeze-keywords : bool
  With this enabled (it is off by default) tailor will use ``-kk`` flag
  on `checkouts` and `updates` to turn off the keyword expansion. This
  may help minimizing the chance of spurious conflicts with later
  merges between different branches.

  *False* by default.

tag-entries : bool
  CVS and CVSPS repositories may turn off automatic tagging of
  entries, that tailor does by default to prevent manual interventions
  in the CVS working copy, using ``tag_entries = False``.

  *True* by default.

darcs
%%%%%

init-options : string
  By default empty, may specify options used to initialize the
  target repository, for example to use the newer ``darcs-2``.

look-for-adds : bool
  By default tailor commits only the entries explicitly mentioned by
  the upstream changeset. Sometimes this is not desiderable, maybe
  even as a quick workaround to a tailor bug. This option allows a
  more relaxed view of life using ``record --look-for-adds``.

replace-badchars : string
  Apparently some darcs repo contains some characters that are illegal
  in an XML stream. This is the case when one uses non-utf8
  accents. To be safe, you can replace them with their xml-safe
  equivalent. The given string must be a regular and valid Python
  dictionary, with each substitution keyed on the character to be
  replaced. By default it's::

    {
      '\xc1': '&#193;',
      '\xc9': '&#201;',
      '\xcd': '&#205;',
      '\xd3': '&#211;',
      '\xd6': '&#214;',
      '\xd5': '&#336;',
      '\xda': '&#218;',
      '\xdc': '&#220;',
      '\xdb': '&#368;',
      '\xe1': '&#225;',
      '\xe9': '&#233;',
      '\xed': '&#237;',
      '\xf3': '&#243;',
      '\xf6': '&#246;',
      '\xf5': '&#337;',
      '\xfa': '&#250;',
      '\xfc': '&#252;',
      '\xfb': '&#369;',
      '\xf1': '&#241;',
      '\xdf': '&#223;',
      '\xe5': '&#229;'
    }

start-revision : string
  Under darcs this may be either the name of a tag or the hash of an
  arbitrary patch in the repository, plus the ordinary ``INITIAL`` or
  ``HEAD`` symbols.

  .. note:: If you want to start from a particular patch, giving its
            hash value as ``start-revision``, you **must** use a
            ``subdir`` different from ``"."``. [#]_

split-initial-changeset-level : integer
  Sometime it's desiderable to avoid the impact of the huge patch
  produced by the bootstrap step, that's basically a snapshot of the
  *whole* working directory. This option controls that: if greater
  than zero, the initial import will be splitted in multiple
  changesets, one per directory not deeper than the specified level. A
  value of 1 will build a changeset for the top level contents
  (directories and files), then a changeset for each subtree. Finally,
  a *tag* will comprehend all the changesets.

  *0* by default.

Big repositories
................

To migrate a big darcs repository it is faster doing a *chunked
approach*, that is using an intermediary repository where you pull say
a couple of hundreds patches at a time from the real source
repository, and then run tailor, in a loop. The following script
illustrates the method::

    mkdir /tmp/intermediary-repo
    cd /tmp/intermediary-repo
    darcs init --darcs-2
    while python -c "print 'y'*200+'d'" | darcs pull --quiet real-source-repo
    do
      tailor -c from-intermediary.tailor
    done

When darcs is the *target*, consider setting a value of 1 or even 2
for the option `split-initial-changeset-level`.

git target
%%%%%%%%%%

parent-repo : string
  Relative path to a git directory to use as a parent.  This is one
  way to import branches into a git repository, which creates a new
  git repository borrowing ancestry from the parent-repo.  It is quite
  a simple way, and thus believed to be quite robust, but spreads
  branches across several git repositories. If this parameter is
  not set, and ``repository`` is not set either, the branch has no
  parent.

  The alternative is to specify a ``repository`` parameter, to contain
  all git branches.  The .git directory in the working copy for each
  branch will then only contain the ``.git/index`` file.

branch : string
  The name of the branch to which to commit.  It is only used in
  single-repository mode (using ``repository``, see above).  The
  default is to use the "master" branch.

branchpoint : string
  A reference to the git commit which is the parent for the first
  revision on the branch to be imported.  It can be a tag name or any
  syntax acceptable by git (eg. something like "tag~2", if you want to
  correct the idea of where the branchpoint is).

  Since tailor generates mostly-stable SHA-1 revisions, you can
  usually also use a SHA-1 as branchpoint.  Just import your trunk
  first, find the correct SHA-1, and setup and import your branch.
  This is especially useful since the current cvs source
  implementation misses many tags.

hg
%%

.. no specific options

monotone
%%%%%%%%

keyid : string
  Monotone key id to use for commits. The specified key
  must exist on keystore. Takes precedence
  over keygenid.

keygenid : string
  Id of a new keypair to generate and store in the
  repository.
  The keypair is used for commits. Ignored if keyid is
  specified.

passphrase : string
  Passphrase to use for commits. Must be specified unless you have one
  on your .monotonerc file

custom-lua : string
  Optional custom lua script. If present, is written into _MTN/monotonerc.

p4
%%

depot-path : string
  The path within the depot indicating the root of all files that will be
  replicated.

  This is used both for determining changes as well as mapping
  file locations from changesets to the filesystem.

  Example:  ``//depot/project/main/``

p4-client : string
  The perforce client spec to use.

  Example:  ``myhostname-tailor``

p4-port : string
  The address of the perforce server.

  Example: ``perforce.mycompany.com:1666``

svn
%%%

filter-badchars : bool (or string)
  Activate (with *True*) or activate and specify (with a *string*) the
  filter on the svn log to eliminate illegal XML characters.

  *False* by default, when set to *True* the following characters are
  washed out from the upstream changes::

    allbadchars = "\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09" \
                  "\x0B\x0C\x0E\x0F\x10\x11\x12\x13\x14\x15" \
                  "\x16\x17\x18\x19\x1A\x1B\x1C\x1D\x1E\x1F\x7f"

  If this is not right or enough, you can specify a string value
  instead of the boolean flag, containing the characters to omit, as
  in::

    filter-badchars=\x00\x01

use-propset : bool
  Indicate that tailor is allowed to properly inject the upstream
  changeset's author and timestamp into the target repository.  As
  stated above, this requires a manual intervention on the repository
  itself and thus is off by default, and tailor simply appends those
  values to the changelog.  When active at bootstrap time and the
  repository is local, tailor creates automatically a minimal
  ``hooks/pre-revprop-change`` script inside the repository, so no
  other intervention is needed.

  *False* by default.

propset-date : bool
  By default *True*, can be used to avoid setting the ``svn:date``
  property on the Subversion revision, and thus problem with
  ``-r{DATE}`` mentioned above.  When this is *False*, the original
  timestamp gets appended to the revision log.

use-limit : bool
  By default *True*, should be set to *False* when using old
  Subversion clients, since ``log --limit`` was introduced with
  version 1.2. By using this option tailor can fetch just the
  revision it needs, instead of transfering whole history log.

commit-all-files : bool
  By default *True*, commits all files from current changeset. Lets
  Subversion check the changes self.
  Set it to *False*, then whish to commits only changed files, that
  tailor detects, perhaps a network speedup.  But a  *False* can be
  insert an extra revision on long dep paths with lot of files. You
  would see two revisions on target, where the source have only one.
  For a true convert should leave it *True*.

trust-root : bool
  Tailor by default verifies that the specified ``repository``
  effectively points to the root of a Subversion repository,
  eventually splitting it and adjusting ``module`` accordingly.  This
  is sometimes undesiderable, for example when the root isn't public
  and cannot be listed.  Setting this option to *True* disable the
  check and tailor takes the given ``repository`` and ``module`` as-is.

ignore-externals : bool
  By default the Subversion backend does not consider the external
  references defined in the source repository.  This option force
  Tailor to behave as it did up to 0.9.20.

svn-tags : string
  Name of the directory used for tags: tailor will copy tagged
  revisions under this directory.

  ``/tags`` by default.

svn-branches : string
  Name of the directory used for branches: tailor will copy branches
  under that directory.

  ``/branches`` by default.

  .. note:: Target module for branches **must** start with ``branches/``.
            Every branch must configure in a single-repository mode.

            Example: ``module = branches/branch.name``

tla
%%%

.. no specific options


.. [#] This is because when you use ``subdir = .`` tailor uses
       ``darcs pull`` instead of ``darcs get``, and the former does
       not accept the option ``--to-match``.


Disjunct working directories
----------------------------

A particular case happens when the ``subdir`` specified in the
*source* is different from the one in *target* as in::

  [tailor-d1-to-d2]
  patch-name-format = ''
  source = darcs:source
  target = darcs:target
  start-revision = INITIAL

  [darcs:source]
  repository = http://darcs.arstecnica.it/tailor
  subdir = tailor_d1

  [darcs:target]
  darcs-command = /usr/local/bin/darcs2
  init-options = --darcs-2
  subdir = tailor_d2

In this particular case, the *kind* may be the same, allowing
particular migrations between the same kind of VC, as showed.

Tailor will use ``rsync`` to move the changes applied in the
source subdirectory to the target one.


Using a Python script as configuration file
-------------------------------------------

Instead of executing ``tailor --configfile project.tailor.conf``
you can prepend the following signature to the config itself::

  #!/usr/bin/env /path/to/tailor

Giving execute mode to it will permit the launch of the tailor
process by running the config script directly::

  $ ./project.tailor.conf

When a config file is signed in this way [#]_, either you pass it as
argument to ``--configfile`` or executed as above, tailor will
actually execute it as a full fledged Python script, that may define
functions that alter the behaviour of tailor itself.

Pre-commit and post-commit hooks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A common usage of this functionality is to define so called `hooks`,
sequences of functions that are executed at particular points in
the tailorization process.

Example 1
%%%%%%%%%

Just to illustrate the functionality, consider the following example::

    #!/usr/bin/env tailor

    """
    [DEFAULT]
    debug = False
    verbose = True

    [project]
    target = bzr:target
    root-directory = /tmp/prova
    state-file = tailor.state
    source = darcs:source
    before-commit = before
    after-commit = after
    start-revision = Almost arbitrarily tagging this as version 0.8

    [bzr:target]
    python-path = /opt/src/bzr.dev
    subdir = bzrside

    [darcs:source]
    repository = /home/lele/WiP/cvsync
    subdir = darcside
    """

    def before(wd, changeset):
        print "BEFORE", changeset
        changeset.author = "LELE"
        return changeset

    def after(wd, changeset):
        print "AFTER", changeset

With the above in a `script` called say ``tester``, just doing::

    $ chmod 755 tester
    $ ./tester

will migrate the history from a darcs repository to a Bazaar one,
forcing the author to a well-known name :-)

Example 2
%%%%%%%%%

A pre commit hook may even alter the content of the files. The
following function replaces the DOS end-of-line convention with the
UNIX one::

    def newlinefix(wd, changeset):
        from pyutil import lineutil
        lineutil.lineify_all_files(wd.basedir, strip=True,
                                   dirpruner=lineutil.darcs_metadir_dirpruner,
                                   filepruner=lineutil.source_code_filepruner)
        return True

It uses zooko's pyutil [#]_ toolset.  Another approach would be looping
over changeset.entries and operating only on added or changed entries.

Example 3
%%%%%%%%%

This loops over the file touched by a particular changeset and tries
to reindent it if it's a Python file::

    def reindent_em(wd, changeset):
        import reindent
        import os

        for entry in changeset.entries:
            fname = os.path.join(wd.basedir, entry.name)

            try:
                if fname[-3:] == '.py':
                    reindent.check(fname)
            except Exception, le:
                print "got an exception from attempt to reindent" \
                      " (maybe that file wasn't Python code?):" \
                      " changeset entry: %s, exception:" \
                      " %s %s %s" % (entry, type(le), repr(le),
                                     hasattr(le, 'args') and le.args,)
                raise le
        return True

You have to find reindent.py in your Python distribution and put it
in your python path. **Beware** that this has some drawbacks: be sure
to read `ticket 8`_ annotations if you use it.

.. [#] Tailor does actually read just the first two bytes from the
       file, and compare them with "#!", so you are free to choose
       whatever syntax works in your environment.

.. [#] Available either at https://yumyum.zooko.com:19144/pub/repos/pyutil
       or http://zooko.com/repos/pyutil.

.. _ticket 8: http://progetti.arstecnica.it/tailor/ticket/8


State file
----------

The state file stores two things: the last upstream revision that
has been applied to the tree, and a sequence of pending (not yet
applied) changesets, that may be empty. In the latter case, tailor
will fetch latest changes from the upstream repository.


Logging
-------

Tailor uses the Python's logging module to emit noise. Its basic
configuration is hardwired and corresponds to the following::

    [formatters]
    keys = console

    [formatter_console]
    format =  %(asctime)s [%(levelname).1s] %(message)s
    datefmt = %H:%M:%S

    [loggers]
    keys = root

    [logger_root]
    level = INFO
    handlers = console

    [handlers]
    keys = console

    [handler_console]
    class = StreamHandler
    formatter = console
    args = (sys.stdout,)
    level = INFO

Another handler is added at runtime that appends any message in a file
named ``projectname.log`` inside the root directory. This file
contains much more details than those usually reaching the console,
and may be of some help to understand what went wrong.

However, you can completely override the default adding a
*supersection* ``[[logging]]`` to the configuration file, something
like::

    # ... usual tailor config ...
    [project]
    source = bzr:source
    target = hg:target

    # Here ends tailor config, and start the one for the logging
    # module

    [[logging]]

    [logger_tailor.BzrRepository]
    level = DEBUG
    handlers = tailor.source

    [handler_tailor.source]
    class = SMTPHandler
    args = ('localhost', 'from@abc', ['tailor@abc'], 'Tailor log')


Further help
============

See the output of ``tailor -h`` for some further tips.  The official
documentation is available as a set of `wiki pages`_ managed by a
Trac_ instance, but there is also `this page`_ on the Darcs wiki
that may give you some other hints.

The development of Tailor is mainly driven by user requests at this
point, and the preferred comunication medium is the dedicated `mailing
list`_ [#]_.

.. _wiki pages:
   http://progetti.arstecnica.it/tailor/

.. _this page:
   http://www.darcs.net/DarcsWiki/Tailor

.. _mailing list:
   http://lists.zooko.com/mailman/listinfo/tailor

.. _trac:
   http://trac.edgewall.org/

I will be more than happy to answer any doubt, question or suggestion
you may have on it. I'm usually hanging out as "lelit" on the
``#tailor`` IRC channel on the `freenode.net` network. Do not hesitate
to contact me either by email or chatting there.

.. [#] I wish to say a big `Thank you` to `Zooko <zooko@zooko.com>`_,
       for hosting the ML and for supporting Tailor in several ways,
       from suggestions to bug reporting and fixing.


Authors
=======

Lele Gaifax <lele@nautilus.homeip.net>

Since I'm not currently using all the supported systems (so little
time, so many VCSs...) I'm not in position to test them out properly,
but I'll do my best to keep them in sync, maybe with your support :-)

Aegis support
-------------

Aegis_ support was contributed by `Walter Franzini
<walter.franzini@gmail.com>`_.

ArX support
-----------

ArX_ support was contributed by `Walter Landry <wlandry@caltech.edu>`_.

Bazaar support
--------------

`Bazaar`_ support was contributed by `Johan Rydberg
<jrydberg@gnu.org>`_.  Nowadays it's being maintained by `Lalo Martins
<lalo.martins@gmail.com>`_.

Git support
-----------

`Git`_ support was contributed by `Todd Mokros
<tmokros@tmokros.net>`_.

Monotone support
----------------

Monotone_ support was kindly contributed by `Markus Schiltknecht
<markus@bluegap.ch>`_ and further developed by `rghetta
<birrachiara@tin.it>`_, that was able to linearize the multi-headed
monotone history into something tailor groks. Kudos!
More recently, `Henry Nestler <henry@bigfoot.de>`_ contributed
various enhancements, like using ``automate`` instead ``list`` and tag
support.

Perforce support
----------------

Perforce_ support was kindly contributed by `Dustin Sallings
<dustin@spy.net>`_.

Tla support
-----------

Tla_ support was contributed by `Robin Farine
<robin.farine@terminus.org>`_.


License
=======

Tailor is `free software`__: you can redistribute it and/or modify
it under the terms of the `GNU General Public License` as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but **without any warranty**; without even the implied warranty of
**merchantability** or **fitness for a particular purpose**.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program in the file ``COPYING``.  If not, see `this
web page`__.

__ http://www.gnu.org/philosophy/free-sw.html
__ http://www.fsf.org/licensing/licenses/gpl.html


About this document
===================

This document and most of the internal documentation use the
reStructuredText format so that it can be easily converted into other
formats, such as HTML.  For more information about this, please see:

  http://docutils.sourceforge.net/rst.html


.. vim:ft=rest
.. Local Variables:
.. mode: rst
.. End:
