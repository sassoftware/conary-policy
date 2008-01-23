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


class NormalizePkgConfig(policy.DestdirPolicy):
    """
    NAME
    ====

    B{C{r.NormalizePkgConfig()}} - Make pkgconfig files multilib-safe

    SYNOPSIS
    ========

    C{r.NormalizePkgConfig([I{filterexp}] || [I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The C{r.NormalizePkgConfig()} policy ensures that pkgconfig files are
    all installed in C{%(libdir)s}, ensuring multilib safety.  If they
    are installed in C{/usr/lib} on a 64-bit system, or in /usr/share
    on any system, the :devellib component is broken for multilib.
    Exceptions to this policy are strongly discouraged.

    EXAMPLES
    ========

    C{r.NormalizePkgConfig(exceptions='/')}

    Effectively disables the C{NormalizePkgConfig} policy.
    """

    processUnmodified = False
    invariantinclusions = [
        '(%(prefix)s/lib|%(datadir)s)/pkgconfig/'
    ]

    def doFile(self, filename):
        libdir = self.recipe.macros.libdir
        destdir = self.recipe.macros.destdir
        basename = os.path.basename(filename)
        if not filename.startswith(libdir):
            dest = util.joinPaths(destdir, libdir, 'pkgconfig', basename)
            if util.exists(dest):
                self.error('%s and %s/%s/%s both exist',
                           filename, libdir, 'pkgconfig', basename)
                return
            util.mkdirChain(os.path.dirname(dest))
            util.rename(destdir+filename, dest)
            try:
                self.recipe.recordMove(destdir+filename, dest)
            except AttributeError:
                pass

class PkgConfigRequires(packagepolicy.BasePluggableRequires):

    invariantinclusions = [ r'(%(libdir)s|%(datadir)s)/pkgconfig/.*\.pc$' ]

    def addPluggableRequirements(self, path, fullpath, pkg, macros):
        # parse pkgconfig file
        variables = {}
        requirements = set()
        libDirs = []
        libraries = set()
        variableLineRe = re.compile('^[a-zA-Z0-9]+=')
        filesRequired = []

        pcContents = [x.strip() for x in file(fullpath).readlines()]
        for pcLine in pcContents:
            # interpolate variables: assume variables are interpreted
            # line-by-line while processing
            pcLineIter = pcLine
            while True:
                for var in variables:
                    pcLineIter = pcLineIter.replace(var, variables[var])
                if pcLine == pcLineIter:
                    break
                pcLine = pcLineIter
            pcLine = pcLineIter

            if variableLineRe.match(pcLine):
                key, val = pcLine.split('=', 1)
                variables['${%s}' %key] = val
            else:
                if (pcLine.startswith('Requires') or
                    pcLine.startswith('Lib')) and ':' in pcLine:
                    keyWord, args = pcLine.split(':', 1)
                    # split on ',' and ' '
                    argList = itertools.chain(*[x.split(',')
                                                for x in args.split()])
                    argList = [x for x in argList if x]
                    if keyWord.startswith('Requires'):
                        versionNext = False
                        for req in argList:
                            if [x for x in '<=>' if x in req]:
                                versionNext = True
                                continue
                            if versionNext:
                                versionNext = False
                                continue
                            requirements.add(req)
                    elif keyWord.startswith('Lib'):
                        for lib in argList:
                            if lib.startswith('-L'):
                                libDirs.append(lib[2:])
                            elif lib.startswith('-l'):
                                libraries.add(lib[2:])
                            else:
                                pass

        # find referenced pkgconfig files and add requirements
        for req in requirements:
            candidateFileNames = [
                '%(destdir)s%(libdir)s/pkgconfig/'+req+'.pc',
                '%(destdir)s%(datadir)s/pkgconfig/'+req+'.pc',
                '%(libdir)s/pkgconfig/'+req+'.pc',
                '%(datadir)s/pkgconfig/'+req+'.pc',
            ]
            candidateFileNames = [ x % macros for x in candidateFileNames ]
            candidateFiles = [ util.exists(x) for x in candidateFileNames ]
            if True in candidateFiles:
                filesRequired.append(
                    (candidateFileNames[candidateFiles.index(True)], 'pkg-config'))
            else:
                self.warn('pkg-config file %s.pc not found', req)
                continue

        # find referenced library files and add requirements
        libraryPaths = sorted(list(self.systemLibPaths))
        for libDir in libDirs:
            if libDir not in libraryPaths:
                libraryPaths.append(libDir)
        for library in libraries:
            found = False
            for libDir in libraryPaths:
                candidateFileNames = [
                    macros.destdir+libDir+'/lib'+library+'.so',
                    macros.destdir+libDir+'/lib'+library+'.a',
                    libDir+'/lib'+library+'.so',
                    libDir+'/lib'+library+'.a',
                ]
                candidateFiles = [ util.exists(x) for x in candidateFileNames ]
                if True in candidateFiles:
                    filesRequired.append(
                        (candidateFileNames[candidateFiles.index(True)], 'library'))
                    found = True
                    break

            if not found:
                self.warn('library file lib%s not found', library)
                continue


        for fileRequired, fileType in filesRequired:
            if fileRequired.startswith(macros.destdir):
                # find requirement in packaging
                fileRequired = util.normpath(fileRequired)
                fileRequired = fileRequired[len(util.normpath(macros.destdir)):]
                autopkg = self.recipe.autopkg
                troveName = autopkg.componentMap[fileRequired].name
                package, component = troveName.split(':', 1)
                if component in ('devellib', 'lib'):
                    for preferredComponent in ('devel', 'devellib'):
                        develTroveName = ':'.join((package, preferredComponent))
                        if develTroveName in autopkg.components and autopkg.components[develTroveName]:
                            # found a non-empty :devel compoment
                            troveName = develTroveName
                            break
                self._addRequirement(path, troveName, [], pkg,
                                     deps.TroveDependencies)
            else:
                troveName = self._enforceProvidedPath(fileRequired,
                                                      fileType=fileType,
                                                      unmanagedError=True)
                if troveName:
                    self._addRequirement(path, troveName, [], pkg,
                                         deps.TroveDependencies)
