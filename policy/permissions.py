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

import os
import stat

from conary.lib import util
from conary.build import policy


class ReadableDocs(policy.DestdirPolicy):
    """
    NAME
    ====

    B{C{r.NormalizePamConfig()}} - Sets documentation file modes

    SYNOPSIS
    ========

    C{r.NormalizePamConfig([I{filterexp}] I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The pluggable policy class C{r.NormalizePamConfig()} is typically
    called from within a Conary recipe to set documentation file modes to
    world-readable.
    
    EXAMPLES
    ========

    FIXME NEED EXAMPLE
    """
    invariantsubtrees = [
        '%(thisdocdir)s/',
        '%(mandir)s/',
        '%(infodir)s/',
    ]

    def doFile(self, path):
        d = self.macros['destdir']
        fullpath = util.joinPaths(d, path)
        mode = os.lstat(fullpath)[stat.ST_MODE]
        if not mode & 0004:
            mode |= 0044
            isExec = mode & 0111
            if isExec:
                mode |= 0011
            self.warn('documentation file %s not group and world readable,'
                      ' changing to mode 0%o', path, mode & 07777)
            os.chmod(fullpath, mode)


class WarnWriteable(policy.EnforcementPolicy):
    """
    NAME
    ====

    B{C{r.WarnWriteable()}} - Warns about writeable files

    SYNOPSIS
    ========

    C{r.WarnWriteable([I{filterexp}] I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The pluggable policy class C{r.WarnWriteable()} is typically
    called from within a Conary recipe to warn about unexpected group- or 
    other-writeable files. 
    
    Rather than set exceptions to this policy, use C{r.SetModes} so that the
    open permissions are explicit and expected.
    
    EXAMPLES
    ========

    FIXME NEED EXAMPLE
    """

    requires = (
        # Needs to run after setModes because setModes sets exceptions
        ('setModes', policy.CONDITIONAL_PRIOR),
    )

    def doFile(self, file):
	fullpath = self.macros.destdir + file
	if os.path.islink(fullpath):
	    return
	if file not in self.recipe.autopkg.pathMap:
	    # directory has been deleted
	    return
	mode = os.lstat(fullpath)[stat.ST_MODE]
	if mode & 022:
	    if stat.S_ISDIR(mode):
		type = "directory"
	    else:
		type = "file"
            self.warn('Possibly inappropriately writeable permission'
                      ' 0%o for %s %s', mode & 0777, type, file)


class WorldWriteableExecutables(policy.EnforcementPolicy):
    """
    NAME
    ====

    B{C{r.WorldWriteableExecutables()}} - Warns about world-writeable executable files

    SYNOPSIS
    ========

    C{r.WorldWriteableExecutables([I{filterexp}] I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The pluggable policy class C{r.WorldWriteableExecutables()} is typically
    called from within a Conary recipe to warn about world-writeable
    executable files
    
    Exceptions to this policy should not be required.
    
    EXAMPLES
    ========

    FIXME NEED EXAMPLE
    """
    # Note that this policy is separate from WarnWriteable because
    # calling r.SetModes should not override this policy automatically.
    invariantexceptions = [ ('.*', stat.S_IFDIR) ]
    def doFile(self, file):
	d = self.macros['destdir']
	mode = os.lstat(util.joinPaths(d, file))[stat.ST_MODE]
        if mode & 0111 and mode & 02 and not stat.S_ISLNK(mode):
            self.error(
                "%s has mode 0%o with world-writeable permission in bindir",
                file, mode)


class IgnoredSetuid(policy.EnforcementPolicy):
    """
    NAME
    ====

    B{C{r.IgnoredSetuid()}} - Warns about world-writeable executable files

    SYNOPSIS
    ========

    C{r.IgnoredSetuid([I{filterexp}] I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The pluggable policy class C{r.IgnoredSetuid()} is typically called from
    within a Conary recipe to warn about files with setuid/setgid bits in the
    filesystem which differ from those explicitly set in the reciped.
    
    Such files will be packaged with no setuid/setid bits set.
    
    EXAMPLES
    ========

    FIXME NEED EXAMPLE
    """
    def doFile(self, path):
	fullpath = self.macros.destdir + path
	mode = os.lstat(fullpath)[stat.ST_MODE]
        pathMap = self.recipe.autopkg.pathMap
        if path not in pathMap:
            return
	if mode & 06000 and not pathMap[path].inode.perms() & 06000:
	    if stat.S_ISDIR(mode):
		type = "directory"
	    else:
		type = "file"
            self.warn('%s %s has unpackaged set{u,g}id mode 0%o in filesystem',
                      type, path, mode&06777)
