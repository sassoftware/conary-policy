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

    The C{r.PHPRequires()} policy identifies php files and adds a
    requirement for the version of php from the system, buildReqs
    or installLabelPath.

    This policy is a sub-policy of C{r.Requires}. It inherits
    the list of exceptions from C{r.Requires}. Under normal
    circumstances, it is not necessary to invoke this policy
    explicitly; call C{r.Requires} instead. However, it may be useful
    to exclude some of the files from being scanned only by this
    policy, in which case using I{exceptions=filterexp} is possible.

    EXAMPLES
    ========

    C{r.PHPRequires(exceptions='.*')}

    Disables the requirement extraction for all files
    """

    invariantinclusions = [r'.*\.php']

    def _isPHPFile(self, fullPath):
        # identify a php file by the presence of the <?php marker
        marker = '<?php'
        f = open(fullPath)
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

    def addPluggableRequirements(self, path, fullpath, pkg, macros):
        if not self._isPHPFile(fullpath):
            return
        cfg = self.recipe.cfg
        db = database.Database(cfg.root, cfg.dbPath)
        repos = self.recipe.getRepos()

        phpPathList = [os.path.join(x, 'php') \
                for x in os.getenv('PATH', '').split(os.pathsep)]
        # add some sane fallback candidates
        for defPath in ('%(bindir)s/php', '%(essentialbindir)s/php'):
            defPath = defPath % macros
            if defPath not in phpPathList:
                phpPathList.append(defPath)
        phpTrove = None
        for phpPath in phpPathList:
            # first, do a direct check of the filesystem.
            if db.pathIsOwned(phpPath):
                troveList = db.iterTrovesByPath(phpPath)
                phpTrove = troveList[0].getName()
                break

        if not phpTrove:
            # then check the buildReqs. we'll drill down to specific files
            # from the package level to ensure we don't introduce conflicting
            # deps for different versions of PHP
            # for example assume php5:lib is in the buildReqs. clearly
            # php5:devel is the correct trove to require
            pkgNames = [x.split(':')[0] for x in self.recipe.buildRequires]
            troveDict = repos.findTroves(cfg.installLabelPath,
                    [(x, None, cfg.buildFlavor) for x in pkgNames],
                    allowMissing = True)
            trvs = repos.getTroves(list(itertools.chain(*troveDict.values())))
            trvs = dict([(x.getName(), x) for x in trvs])
            for pkgName in pkgNames:
                pkgTrv = trvs[pkgName]
                for pkgComp in repos.getTroves(list(pkgTrv.iterTroveList( \
                        strongRefs = True, weakRefs = True))):
                    if [x[1] for x in pkgComp.iterFileList() if x[1] in phpPathList]:
                        phpTrove = pkgComp.getName()

        if not phpTrove:
            # last resort: check for php on the installLabelPath from the repo
            for lbl in cfg.installLabelPath:
                if phpTrove:
                    # we found a satisfactory trove on phpPathList. quit looking
                    break
                pathDict = repos.getTroveLeavesByPath(phpPathList, lbl)
                for phpPath in phpPathList:
                    # find the first trove on the installLabelPath that
                    # provides a path to php. warn on multiple matches.
                    phpPkgList = list(set(x[0] for x in pathDict[phpPath]))
                    if len(phpPkgList) == 1:
                        phpTrove = phpPkgList[0]
                        break
                    elif len(phpPkgList):
                        self.warn("'%s' requires PHP, which is provided by " \
                                "multiple troves. Add one of the following " \
                                "troves to the recipe's buildRequires to " \
                                "satisfy this dependency: ('%s')" % \
                                (path, "', '".join(phpPkgList)))
                        return

        if phpTrove:
            self._addRequirement(path, phpTrove, [], pkg,
                                 deps.TroveDependencies)
        else:
            self.warn("'%s' requires PHP, which is not provided by any " \
                    "troves. Please add a trove that provides the PHP " \
                    "interpreter to your buildRequires." % path)
