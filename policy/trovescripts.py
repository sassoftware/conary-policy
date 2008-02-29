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

import os

from conary.lib import util
from conary.build import policy


class _TroveScript(policy.PackagePolicy):
    processUnmodified = False
    keywords = { 'contents' : None }

    _troveScriptName = None

    def __init__(self, *args, **keywords):
        policy.PackagePolicy.__init__(self, *args, **keywords)

    def updateArgs(self, *args, **keywords):
        if args:
            troveNames = args
        else:
            troveNames = [ self.recipe.name ]
        self.troveNames = troveNames
        policy.PackagePolicy.updateArgs(self, **keywords)

    def do(self):
        if not self.contents:
            return

        if not hasattr(self.recipe, '_addTroveScript'):
            # Older conary, no support for trove scripts
            return

        # Build component map
        availTroveNames = dict((x.name, None) for x in
                                self.recipe.autopkg.getComponents())
        availTroveNames.update(self.recipe.packages)
        troveNames = set(self.troveNames) & set(availTroveNames)

        # We don't support compatibility classes for troves (yet)
        self.recipe._addTroveScript(troveNames, self.contents,
            self._troveScriptName, None)

class ScriptPreUpdate(_TroveScript):
    _troveScriptName = 'preUpdate'

class ScriptPostUpdate(_TroveScript):
    _troveScriptName = 'postUpdate'

class ScriptPreInstall(_TroveScript):
    _troveScriptName = 'preInstall'

class ScriptPostInstall(_TroveScript):
    _troveScriptName = 'postInstall'

class ScriptPreErase(_TroveScript):
    _troveScriptName = 'preErase'

class ScriptPostErase(_TroveScript):
    _troveScriptName = 'postErase'

class ScriptPostRollback(_TroveScript):
    _troveScriptName = 'postRollback'
