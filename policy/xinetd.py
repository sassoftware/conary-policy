#
# Copyright (c) rPath, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from conary.build import policy, packagepolicy
from conary.deps import deps

if hasattr(packagepolicy, '_basePluggableRequires'):
    _basePluggableRequires = packagepolicy._basePluggableRequires
else:
    # Older Conary. Make the class inherit from object; this policy
    # will then be ignored.
    _basePluggableRequires = object

class XinetdConfigRequires(_basePluggableRequires):
    """
    NAME
    ====

    B{C{r.XinetdConfigRequires()}} - Automatically add an appropriate
    requirement on xinetd for packages containing an xinetd configuration
    file.

    SYNOPSIS
    ========

    C{r.XinetdConfigRequires([I{filterexp}] || [I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The C{r.XinetdConfigRequires()} policy adds a requirement of
    C{xinetd:runtime} for packages containing an xinetd configuration file.

    The dependency is added only if the service is enabled by default.

    This policy is a sub-policy of C{r.Requires}. It inherits
    the list of exceptions from C{r.Requires}. Under normal
    circumstances, it is not necessary to invoke this policy
    explicitly; call C{r.Requires} instead. However, it may be useful
    to exclude some of the files from being scanned only by this
    policy, in which case using I{exceptions=filterexp} is possible.

    EXAMPLES
    ========

    C{r.XinetdConfigRequires(exceptions='mylo')}

    Disables adding xinetd requirements for the C{/etc/xinetd.d/mylo}
    file.
    """

    requires = (
        ('ResolveFileDependencies', policy.REQUIRED_PRIOR),
    )
    invariantinclusions = [ r'%(sysconfdir)s/xinetd.d/' ]

    def addPluggableRequirements(self, path, fullpath, pkgFiles, macros):

        # parse file
        fContents = [x.strip() for x in file(fullpath).readlines()]
        # Although the line says "disable", we use "enabled", so that if the
        # line is not present at all we don't generate the dep
        enabled = None
        for fLine in fContents:
            if not fLine or fLine[0] == '#':
                continue
            arr = [x.strip() for x in fLine.split('=', 1) ]
            if len(arr) != 2:
                continue
            if arr[0] != 'disable':
                continue
            enabled = ((arr[1] == 'no') and True) or False
            break

        if not enabled:
            return

        # ResolveFileDependencies will convert this to a trove
        # dependency if the file dependency is not satisfied
        self._addRequirement(path, "/usr/sbin/xinetd", [], pkgFiles,
                             deps.FileDependencies)
