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
    Remove classes of files that normally should not be packaged;
    C{r.RemoveNonPackageFiles(exceptions=I{filterexpression})}
    allows one of these files to be included in a package.
    """
    requires = (
        ('Strip', policy.CONDITIONAL_PRIOR),
    )
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
