#
# Copyright (c) 2007 rPath, Inc.
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

class XinetdConfigRequires(packagepolicy.Requires):
    requires = [
        ('Requires', policy.REQUIRED_SUBSEQUENT)
    ]

    invariantinclusions = [ r'%(sysconfdir)s/xinetd.d/.*$' ]

    def preProcess(self):
        exceptions = self.recipe._policyMap['Requires'].exceptions
        if exceptions:
            packagepolicy.Requires.updateArgs(self, exceptions=exceptions)
        exceptDeps = self.recipe._policyMap['Requires'].exceptDeps
        if exceptDeps:
            self.exceptDeps.extend(exceptDeps)

        return packagepolicy.Requires.preProcess(self)

    def doFile(self, path):
        componentMap = self.recipe.autopkg.componentMap
        if path not in componentMap:
            return
        pkg = componentMap[path]
        f = pkg.getFile(path)
        macros = self.recipe.macros
        fullpath = macros.destdir + path

        self._addXinetdConfigRequirements(path, fullpath, pkg, macros)

        self.whiteOut(path, pkg)
        self.unionDeps(path, pkg, f)

    def _addXinetdConfigRequirements(self, path, fullpath, pkg, macros):
        # parse config file

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
