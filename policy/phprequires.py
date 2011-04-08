#
# Copyright (c) 2011 rPath, Inc.
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

import errno
import itertools
import os

from conary.build import packagepolicy

from conary.deps import deps
from conary.local import database

# copied from pkgconfig.py
if hasattr(packagepolicy, '_basePluggableRequires'):
    _basePluggableRequires = packagepolicy._basePluggableRequires
else:
    # Older Conary. Make the class inherit from object; this policy
    # will then be ignored.
    _basePluggableRequires = object

class PHPRequires(_basePluggableRequires):
    """
    NAME
    ====

    B{C{r.PHPRequires()}} - Determine PHP interpreter and add requirement
    for .php files.

    SYNOPSIS
    ========

    C{r.PHPRequires([I{filterexp}] || [I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The C{r.PHPRequires()} policy identifies PHP files and adds a
    requirement for the appropriate trove containing the correct
    version of the php interpreter from the system, buildRequires,
    or installLabelPath.

    This policy is a sub-policy of C{r.Requires}.  It inherits
    the list of exceptions from C{r.Requires}.  Under normal
    circumstances, it is not necessary to invoke this policy
    explicitly; call C{r.Requires} instead. However, it may be useful
    to exclude some of the files from being scanned only by this
    policy, in which case using I{exceptions=filterexp} is possible.

    EXAMPLES
    ========

    C{r.PHPRequires(exceptions='.*')}

    Disables the PHP requirement determination for all files.
    """

    invariantinclusions = [r'.*\.php']

    def __init__(self, *args, **kwargs):
        _basePluggableRequires.__init__(self, *args, **kwargs)
        self.phpTrove = None
        self.phpPathList = []

        self.cfg = self.recipe.cfg
        self.repos = None # Delay fetching repository until it is available

    def _isPHPFile(self, fullPath):
        # confirm identity of a PHP file by the presence of the <?php marker
        marker = '<?php'
        try:
            f = open(fullPath)
        except IOError, err:
            if err.errno == errno.ENOENT:
                # No such file, probably because it is a dead symlink.
                return False
            raise
        f.seek(0, 2)
        limit = f.tell()
        f.seek(0)
        buf = f.read(4096)
        while True:
            if marker in buf:
                return True
            if f.tell() == limit:
                return False
            # add the last 5 chars to the end to ensure we don't break a marker
            buf = buf[-5:] + f.read(4096)

    def _getPHPPathCandidateList(self):
        phpBinNames = ('php', 'php5')
        macroPaths = [ x % self.recipe.macros for x in
                        ('%(bindir)s', '%(essentialbindir)s') ]
        for path in os.getenv('PATH', '').split(os.pathsep) + macroPaths:
            for bin in phpBinNames:
                binPath = os.path.join(path, bin)
                if binPath not in self.phpPathList:
                    self.phpPathList.append(binPath)

    def _checkLocalSystem(self, path):
        db = database.Database(self.cfg.root,
                               self.cfg.dbPath)
        for phpPath in self.phpPathList:
            # first, do a direct check of the filesystem.
            if db.pathIsOwned(phpPath):
                troveList = db.iterTrovesByPath(phpPath)
                return troveList[0].getName()

    def _checkBuildRequires(self, path):
        # then check the buildReqs. we'll drill down to specific files
        # from the package level to ensure we don't introduce conflicting
        # deps for different versions of PHP
        # for example assume php5:devel is in the buildReqs. clearly
        # php5:lib is the correct trove to require
        pkgNames = [ x.split(':')[0] for x in self.recipe.buildRequires ]

        troveDict = self.repos.findTroves(
            self.cfg.installLabelPath,
            [ (x, None, self.cfg.buildFlavor) for x in pkgNames ],
            allowMissing = True
        )

        trvs = self.repos.getTroves(list(itertools.chain(*troveDict.values())))
        trvs = dict([ (x.getName(), x) for x in trvs ])

        for pkgName in pkgNames:
            pkgTrv = trvs.get(pkgName)
            if not pkgTrv:
                continue

            for pkgComp in self.repos.getTroves(list(pkgTrv.iterTroveList(
                    strongRefs = True, weakRefs = True))):
                if [ x[1] for x in pkgComp.iterFileList()
                          if x[1] in self.phpPathList ]:
                    return pkgComp.getName()

    def _checkRepository(self, path):
        # nothing in buildRequires specifies any particular php
        # package.
        # last resort: check for php on the installLabelPath from the repo
        for lbl in self.cfg.installLabelPath:
            pathDict = self.repos.getTroveLeavesByPath(self.phpPathList, lbl)
            for phpPath in self.phpPathList:
                # find the first trove on the installLabelPath that
                # provides a path to php. warn on multiple matches.
                phpPkgList = set(x[0] for x in pathDict[phpPath])
                if len(phpPkgList) == 1:
                    return phpPkgList.pop()
                elif len(phpPkgList):
                    self.warn("'%s' requires PHP, which is provided by " \
                            "multiple troves. Add one of the following " \
                            "troves to the recipe's buildRequires to " \
                            "satisfy this dependency: ('%s')" % \
                            (path, "', '".join(phpPkgList)))
                    return False

    def addPluggableRequirements(self, path, fullpath, pkgFiles, macros):
        if not self._isPHPFile(fullpath):
            return
        if self.repos is None:
            self.repos = self.recipe.getRepos()

        # No phpTrove has been found, return.
        if self.phpTrove == False:
            return

        if self.phpTrove is None:
            self._getPHPPathCandidateList()

            for check in (self._checkLocalSystem,
                          self._checkBuildRequires,
                          self._checkRepository):

                self.phpTrove = check(path)
                if self.phpTrove:
                    break

                # Avoid printing an additional warning message if one has
                # already been printed from the checkRepository method.
                elif self.phpTrove == False:
                    return

        if self.phpTrove:
            self.info('Adding dependency on %s for file %s',
                self.phpTrove, path)
            self._addRequirement(path, self.phpTrove, [], pkgFiles,
                                 deps.TroveDependencies)
        else:
            self.phpTrove = False
            self.warn("'%s' requires PHP, which is not provided by any " \
                    "troves. Please add a trove that provides the PHP " \
                    "interpreter to your buildRequires." % path)
