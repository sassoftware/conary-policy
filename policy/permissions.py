#
# Copyright (c) 2004-2006 rPath, Inc.
#
# This program is distributed under the terms of the Common Public License,
# version 1.0. A copy of this license should have been distributed with this
# source file in a file called LICENSE. If it is not present, the license
# is always available at http://www.rpath.com/permanent/licenses/CPL-1.0.
#
# This program is distributed in the hope that it will be useful, but
# without any warranty; without even the implied warranty of merchantability
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

    B{C{r.ReadableDocs()}} - Sets documentation file modes

    SYNOPSIS
    ========

    C{r.ReadableDocs([I{filterexp}] I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    C{r.ReadableDocs()} policy sets documentation file modes to
    world-readable.  This policy should not require exceptions.
    """
    processUnmodified = False
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

    B{C{r.WarnWriteable()}} - Warns about unexpectedly writeable files

    SYNOPSIS
    ========

    C{r.WarnWriteable([I{filterexp}] I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The C{r.WarnWriteable()} policy warns about unexpected group-writeable,
    or other-writeable files.

    Rather than set exceptions to this policy, use C{r.SetModes} so that the
    open permissions are explicit and expected.
    """

    requires = (
        # Needs to run after setModes because setModes sets exceptions
        ('setModes', policy.CONDITIONAL_PRIOR),
        # Needs to run after Ownership for group info
        ('Ownership', policy.REQUIRED_PRIOR),
    )
    processUnmodified = False

    def doFile(self, filename):
        fullpath = self.macros.destdir + filename
	if os.path.islink(fullpath):
	    return
        if filename not in self.recipe.autopkg.pathMap:
	    # directory has been deleted
	    return
	mode = os.lstat(fullpath)[stat.ST_MODE]
        group = self.recipe.autopkg.pathMap[filename].inode.group()
        if mode & 02 or (mode & 020 and group != 'root'):
	    if stat.S_ISDIR(mode):
		type = "directory"
	    else:
		type = "file"
            self.warn('Possibly inappropriately writeable permission'
                      ' 0%o for %s %s', mode & 0777, type, filename)


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

    The C{r.WorldWriteableExecutables()} policy warns about world-writeable
    executable files

    Exceptions to this policy should not be required.
    """
    processUnmodified = False
    # Note that this policy is separate from WarnWriteable because
    # calling r.SetModes should not override this policy automatically.
    invariantexceptions = [ ('.*', stat.S_IFDIR) ]
    def doFile(self, file):
	d = self.macros['destdir']
	mode = os.lstat(util.joinPaths(d, file))[stat.ST_MODE]
        if mode & 0111 and mode & 02 and not stat.S_ISLNK(mode):
            self.error(
                "%s has executable mode 0%o with world-writeable permission",
                file, mode)


class IgnoredSetuid(policy.EnforcementPolicy):
    """
    NAME
    ====

    B{C{r.IgnoredSetuid()}} - Warns about potentially missing setuid bits

    SYNOPSIS
    ========

    C{r.IgnoredSetuid([I{filterexp}] I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The C{r.IgnoredSetuid()} policy warns about files with setuid/setgid
    bits in the filesystem which differ from those explicitly set in the
    recipe.

    Such files will be packaged with no setuid/setid bits set.

    Instead of providing an exception to this policy, use the
    C{r.SetModes} command to explicitly set the setuid/setgid bits.
    """
    processUnmodified = False
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
