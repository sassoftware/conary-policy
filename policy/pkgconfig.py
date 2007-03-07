#
# Copyright (c) 2007 rPath, Inc.
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

from conary.build import policy
from conary.lib import util


class NormalizePkgConfig(policy.DestdirPolicy):
    """
    NAME
    ====

    B{C{r.NormalizePkgConfig()}} - Make pkgconfig files multilib-safe

    SYNOPSIS
    ========

    C{r.NormalizePkgConfig([I{filterexp}] || [I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The C{r.NormalizePkgConfig()} policy ensures that pkgconfig files are
    all installed in C{%(libdir)s}, ensuring multilib safety.  If they
    are installed in C{/usr/lib} on a 64-bit system, or in /usr/share
    on any system, the :devellib component is broken for multilib.
    Exceptions to this policy are strongly discouraged.

    EXAMPLES
    ========

    C{r.NormalizePkgConfig(exceptions='/')}

    Effectively disables the C{NormalizePkgConfig} policy.
    """

    processUnmodified = False
    invariantinclusions = [
        '(%(prefix)s/lib|%(datadir)s)/pkgconfig/'
    ]

    def doFile(self, filename):
        libdir = self.recipe.macros.libdir
        destdir = self.recipe.macros.destdir
        basename = os.path.basename(filename)
        if not filename.startswith(libdir):
            dest = util.joinPaths(destdir, libdir, 'pkgconfig', basename)
            if util.exists(dest):
                self.error('%s and %s/%s/%s both exist',
                           filename, libdir, 'pkgconfig', basename)
                return
            util.mkdirChain(os.path.dirname(dest))
            util.rename(destdir+filename, dest)
