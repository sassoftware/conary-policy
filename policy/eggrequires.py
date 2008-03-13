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
import pkg_resources

from conary.build import packagepolicy
from conary.deps import deps
from conary.lib import util
from conary.lib import fixedglob

# copied from pkgconfig.py
if hasattr(packagepolicy, '_basePluggableRequires'):
    _basePluggableRequires = packagepolicy._basePluggableRequires
else:
    # Older Conary. Make the class inherit from object
    _basePluggableRequires = object

class EggRequires(packagepolicy._basePluggableRequires):
    """
    NAME
    ====

    B{C{r.EggRequires()}} - Extract dependency information out of
    egg-info requires.txt files.

    SYNOPSIS
    ========

    C{r.EggRequires([I{filterexp}] || [I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The C{r.EggRequires()} policy parses pkg-config files and extracts
    dependency information.

    This policy is a sub-policy of C{r.Requires}. It inherits the list
    of exceptions from C{r.Requires}. Under normal circumstances, it is not
    needed to invoke it explicitly. However, it may be necessary to exclude
    some of the files from being scanned, in which case using
    I{exceptions=filterexp} is possible.

    EXAMPLES
    ========

    C{r.EggRequires(exceptions='.*/foo[^/]\.egg-info/requires.txt')}

    Disables the requirement extraction for foo's egg-info.
    """

    invariantinclusions = [r'%(libdir)s/python.*\.egg-info/requires.txt',
            r'%(prefix)s/lib/python.*\.egg-info/requires.txt']

    def _parseEggRequires(self, fullpath):
        eggDir = os.path.dirname(fullpath)
        baseDir = os.path.dirname(eggDir)
        metadata = pkg_resources.PathMetadata(baseDir, eggDir)
        distName = os.path.splitext(os.path.basename(eggDir))[0]
        dist = pkg_resources.Distribution(baseDir,
                project_name = distName, metadata = metadata)


        mandatoryReqs = [x.project_name for x in dist.requires()]
        allReqs = [x.project_name for x in dist.requires(dist.extras)]
        optionalReqs = [x for x in allReqs if x not in mandatoryReqs]
        return mandatoryReqs, optionalReqs

    def addPluggableRequirements(self, path, fullpath, pkg, macros):
        mandatoryReqs, optionalReqs = self._parseEggRequires(fullpath)
        filesRequired = []
        for req in itertools.chain(mandatoryReqs, optionalReqs):
            candidatePrefs = [
                '%(destdir)s%(libdir)s/python*/',
                '%(destdir)s%(prefix)s/lib/python*/',
                '%(destdir)s%(libdir)s/python*/site-packages/',
                '%(destdir)s%(prefix)s/lib/python*/site-packages/',
                '%(libdir)s/python*/',
                '%(prefix)s/lib/python*/',
                '%(libdir)s/python*/site-packages/',
                '%(prefix)s/lib/python*/site-packages/',
                    ]
            candidateFileNames = [(x + req + '*.egg-info/PKG-INFO') % macros \
                    for x in candidatePrefs]
            candidateFiles = [fixedglob.glob(x) for x in candidateFileNames]
            candidateFiles = [x[0] for x in candidateFiles if x]
            if candidateFiles:
                filesRequired.append(candidateFiles[0])
            else:
                if req in mandatoryReqs:
                    self.warn('Python egg-info for %s was not found', req)

        for fileRequired in filesRequired:
            troveName = None
            if fileRequired.startswith(macros.destdir):
                # find requirement in packaging
                fileRequired = util.normpath(fileRequired)
                fileRequired = fileRequired[len(util.normpath(macros.destdir)):]
                autopkg = self.recipe.autopkg
                troveName = autopkg.componentMap[fileRequired].name
            else:
                troveName = self._enforceProvidedPath(fileRequired,
                                                      fileType='egg-info',
                                                      unmanagedError=True)
            if troveName:
                self._addRequirement(path, troveName, [], pkg,
                                     deps.TroveDependencies)
