#
# Copyright (c) 2008 rPath, Inc.
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

import itertools
import os
import re

from conary.build import policy, packagepolicy
from conary.deps import deps
from conary.lib import util

class XinetdConfigRequires(packagepolicy._basePluggableRequires):
    """
    NAME
    ====

    B{C{r.XinetdConfigRequires()}} - Automatically add a dependency on
    C{xinetd:runtime} for packages containing an xinetd configuration file.

    SYNOPSIS
    ========

    C{r.XinetdConfigRequires([I{filterexp}] || [I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The C{r.XinetdConfigRequires()} policy adds a dependency on
    C{xinetd:runtime} for packages containing an xinetd configuration file.

    The dependency is added only if the service is enabled by default.

    This policy is a sub-policy of C{r.Requires}. It inherits the list
    of exceptions from C{r.Requires}. Under normal circumstances, it is not
    needed to invoke it explicitly. However, it may be necessary to exclude
    some of the files from being scanned, in which case using
    I{exceptions=filterexp} is possible.

    EXAMPLES
    ========

    C{r.XinetdConfigRequires(exceptions='mylo')}

    Disables the scanning of C{mylo}.
    """

    invariantinclusions = [ r'%(sysconfdir)s/xinetd.d/.*$' ]

    def addPluggableRequirements(self, path, fullpath, pkg, macros):

        # parse file
        fContents = [x.strip() for x in file(fullpath).readlines()]
        # Although the line says "disable", we use "enabled", so that if the
        # line is not present at all we don't generate the dep
        enabled = None
        for fLine in fContents:
            if fLine[0] == '#':
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
        self._addRequirement(path, "xinetd:runtime", [], pkg,
                             deps.TroveDependencies)
