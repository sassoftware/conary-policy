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

from conary.build import packagepolicy
from conary.deps import deps
from conary.lib import util
from conary.lib import fixedglob

# copied from pkgconfig.py
if hasattr(packagepolicy, '_basePluggableRequires'):
    _basePluggableRequires = packagepolicy._basePluggableRequires
else:
    # Older Conary. Make the class inherit from object; this policy
    # will then be ignored.
    _basePluggableRequires = object

class EggRequires(_basePluggableRequires):
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

    This policy is a sub-policy of C{r.Requires}. It inherits
    the list of exceptions from C{r.Requires}. Under normal
    circumstances, it is not necessary to invoke this policy
    explicitly; call C{r.Requires} instead. However, it may be useful
    to exclude some of the files from being scanned only by this
    policy, in which case using I{exceptions=filterexp} is possible.

    EXAMPLES
    ========

    C{r.EggRequires(exceptions='.*/foo[^/]\.egg-info/requires.txt')}

    Disables the requirement extraction for foo's egg-info.
    """

    invariantinclusions = [r'%(libdir)s/python.*\.egg-info/requires.txt',
            r'%(prefix)s/lib/python.*\.egg-info/requires.txt']

    def __init__(self, *args, **kw):
        self._checkedForPythonSetupTools = False
        packagepolicy._basePluggableRequires.__init__(self, *args, **kw)

    def _checkForPythonSetupTools(self, fullpath):
        self.transitiveBuildRequires = self.recipe._getTransitiveBuildRequiresNames()
        if 'python-setuptools:python' not in self.transitiveBuildRequires:
            self.recipe.reportMissingBuildRequires('python-setuptools:python')
            if 'local@local' in self.recipe.macros.buildlabel:
                logFn = self.warn
            else:
                logFn = self.error
            logFn("add 'python-setuptools:python' to buildRequires to inspect %s", fullpath)
            return False
        # do not recommend removing 'python-setuptools:python' from buildReqs
        try:
            self.recipe.reportExcessBuildRequires('python-setuptools:python')
        except AttributeError:
            # older conary
            pass
        return True

    def _parseEggRequires(self, path, fullpath):
        if not self._checkedForPythonSetupTools:
            if not self._checkForPythonSetupTools(path):
                try:
                    import pkg_resources
                except ImportError:
                    self.pkg_resources = None
                    return [], []
            else:
                import pkg_resources
            self.pkg_resources = pkg_resources
            self._checkedForPythonSetupTools = True
        elif self.pkg_resources is None:
            # we checked and could not import pkg_resources
            return [], []
        eggDir = os.path.dirname(fullpath)
        baseDir = os.path.dirname(eggDir)
        metadata = self.pkg_resources.PathMetadata(baseDir, eggDir)
        distName = os.path.splitext(os.path.basename(eggDir))[0]
        dist = self.pkg_resources.Distribution(baseDir,
                                project_name = distName, metadata = metadata)


        mandatoryReqs = [x.project_name for x in dist.requires()]
        allReqs = [x.project_name for x in dist.requires(dist.extras)]
        optionalReqs = [x for x in allReqs if x not in mandatoryReqs]
        return mandatoryReqs, optionalReqs

    def addPluggableRequirements(self, path, fullpath, pkgFiles, macros):
        mandatoryReqs, optionalReqs = self._parseEggRequires(path, fullpath)
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
                fileRequired = util.normpath(os.path.realpath(fileRequired))
                fileRequired = fileRequired[len(util.normpath(macros.destdir)):]
                autopkg = self.recipe.autopkg
                troveName = autopkg.findComponent(fileRequired).getName()
            else:
                troveName = self._enforceProvidedPath(fileRequired,
                                                      fileType='egg-info',
                                                      unmanagedError=True)
            if troveName:
                self._addRequirement(path, troveName, [], pkgFiles,
                                     deps.TroveDependencies)
