#
# Copyright (c) 2004-2006 rPath, Inc.
#
# This program is distributed under the terms of the Common Public License,
# version 1.0. A copy of this license should have been distributed with this
# source file in a file called LICENSE. If it is not present, the license
# is always available at http://www.opensource.org/licenses/cpl.php.
#
# This program is distributed in the hope that it will be useful, but
# without any waranty; without even the implied warranty of merchantability
# or fitness for a particular purpose. See the Common Public License for
# full details.
#

from conary.lib import util
from conary.build import policy


class RemoveNonPackageFiles(policy.DestdirPolicy):
    """
    NAME
    ====

    B{C{r.RemoveNonPackageFiles()}} - Remove classes of files that should not
    be packaged

    SYNOPSIS
    ========

    C{r.RemoveNonPackageFiles([I{filterexp}] I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The C{r.RemoveNonPackageFiles()} class is  called from within a Conary
    recipe to remove classes of files that  normally should not be packaged

    EXAMPLES
    ========

    FIXME NEED EXAMPLE
    """
    invariantinclusions = [
        r'\.la$',
        # python .a's might have been installed in the wrong place on multilib
        r'%(prefix)s/(lib|%(lib)s)/python.*/site-packages/.*\.a$',
        r'perllocal\.pod$',
        r'\.packlist$',
        r'\.cvsignore$',
        r'\.orig$',
        r'%(sysconfdir)s.*/rc[0-6].d/[KS].*$',
        '~$',
        r'.*/\.#.*',
        '/(var/)?tmp/',
        r'.*/fonts.(cache.*|dir|scale)$',
    ]

    def doFile(self, path):
        self.info("Removing %s", path)
        util.remove(self.macros['destdir']+path, quiet=True)
