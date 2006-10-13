#
# Copyright (c) 2005-2006 rPath, Inc.
#
# This program is distributed under the terms of the Common Public License,
# version 1.0. A copy of this license should have been distributed with this
# source file in a file called LICENSE. If it is not present, the license
# is always available at http://www.opensource.org/licenses/cpl.php.
#
# This program is distributed in the hope that it will be useful, but
# without any warranty; without even the implied warranty of merchantability
# or fitness for a particular purpose. See the Common Public License for
# full details.
#

import os
import shutil
import stat

from conary.build import policy
from conary.lib import util


class AutoDoc(policy.DestdirPolicy):
    """
    NAME
    ====

    B{C{r.AutoDoc()}} - Adds likely documentation not otherwise installed

    SYNOPSIS
    ========

    C{r.AutoDoc([I{filterexp}] || [I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The C{r.AutoDoc()} policy ensures likely documentation not otherwise
    installed is added automatically. Exceptions to the policy are
    passed in via C{r.AutoDoc(I{exceptions=filterexpression})}. Exceptions
    are evaluated relative to the build directory, and not the destination
    directory. All files created will have modes of 644.

    EXAMPLES
    ========

    C{r.AutoDoc('COPYRIGHT.PATENT', 'GPL_LICENSE.txt')}

    Adds the documentation files C{COPYRIGHT.PATENT}, and C{GPL_LICENSE.txt},
    wherever they are found in the source tree.

    C{r.AutoDoc(exceptions='/')}

    Effectively disables the C{AutoDoc} policy.

    C{r.AutoDoc(exceptions='foo/TODO')}

    Prevents any file whose pathname includes C{foo/TODO} from
    being added to the package by the C{AutoDoc} policy, while
    still allowing the C{AutoDoc} policy to add other C{TODO}
    files to the package.
    """

    requires = (
        ('ReadableDocs', policy.CONDITIONAL_SUBSEQUENT),
    )
    rootdir = '%(builddir)s'
    invariantinclusions = [
        '.*/NEWS$',
        r'.*/(LICENSE|COPY(ING|RIGHT))(\.(lib|txt)|)$',
        '.*/RELEASE-NOTES$',
        '.*/HACKING$',
        '.*/NOTICE.txt$',
        '.*/INSTALL$',
        '.*README.*',
        '.*/CHANGES$',
        '.*/TODO$',
        '.*/FAQ$',
        '.*/Change[lL]og.*',
    ]
    invariantexceptions = [ ('.*', stat.S_IFDIR) ]

    def preProcess(self):
        m = self.recipe.macros
        self.builddir = m.builddir
        self.destdir = util.joinPaths(m.destdir, m.thisdocdir)

    def doFile(self, filename):
        source = util.joinPaths(self.builddir, filename)
        dest = util.joinPaths(self.destdir, filename)
        if os.path.exists(dest):
            return
        if not util.isregular(source):
            # will not be a directory, but might be a symlink or something
            return
        util.mkdirChain(os.path.dirname(dest))
        shutil.copy2(source, dest)
        os.chmod(dest, 0644)
        # this file should not be counted as making package non-empty
        self.recipe._autoCreatedFileCount += 1
