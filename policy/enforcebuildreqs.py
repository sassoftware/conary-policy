#
# Copyright (c) 2005-2006 rPath, Inc.
#
# This program is distributed under the terms of the Common Public License,
# version 1.0. A copy of this license should have been distributed with this
# source file in a file called LICENSE. If it is not present, the license
# is always available at http://www.opensource.org/licenses/cpl.php.
#
# This program is distributed in the hope that it will be useful, but
# without any waranty; without even the implied warranty of merchantability
# or fitness for a particular purpose. See the Common Public License for
# full details.
#

import os
import re
import stat

from conary.deps import deps
from conary.lib import util
from conary.local import database
from conary.build import policy
from conary.build.use import Use


class _enforceBuildRequirements(policy.EnforcementPolicy):
    """
    Pure virtual base class from which classes are derived that
    enforce buildRequires population from runtime dependencies.
    """
    def preProcess(self):
        self.compExceptions = set()
        if self.exceptions:
            for exception in self.exceptions:
                self.compExceptions.add(exception % self.recipe.macros)
        self.exceptions = None

        # right now we do not enforce branches.  This could be
        # done with more work.  There is no way I know of to
        # enforce flavors, so we just remove them from the spec.
        self.truncatedBuildRequires = set(
            self.recipe.buildReqMap[spec].getName()
            for spec in self.recipe.buildRequires
            if spec in self.recipe.buildReqMap)

	components = self.recipe.autopkg.components
        reqDepSet = deps.DependencySet()
        provDepSet = deps.DependencySet()
        for pkg in components.values():
            reqDepSet.union(pkg.requires)
            provDepSet.union(pkg.provides)
        self.depSet = deps.DependencySet()
        self.depSet.union(reqDepSet - provDepSet)

        self.setTalk()

    def test(self):
        localDeps = self.depSet.getDepClasses().get(self.depClassType, None)
        if not localDeps:
            return False

        depSetList = [ ]
        for dep in localDeps.getDeps():
            depSet = deps.DependencySet()
            depSet.addDep(self.depClass, dep)
            depSetList.append(depSet)

        cfg = self.recipe.cfg
        self.db = database.Database(cfg.root, cfg.dbPath)
        self.localProvides = self.db.getTrovesWithProvides(depSetList)
        self.unprovided = [x for x in depSetList if x not in self.localProvides]

        return True

    def postProcess(self):
        del self.db

    def setTalk(self):
        # FIXME: remove "True or " when we are ready for errors
        if (True or 'local@local' in self.recipe.macros.buildlabel
            or Use.bootstrap._get()):
            self.talk = self.warn
        else:
            self.talk = self.error

    def do(self):
        missingBuildRequires = set()
        missingBuildRequiresChoices = []

	components = self.recipe.autopkg.components
        pathMap = self.recipe.autopkg.pathMap
        pathReqMap = {}

        for dep in self.localProvides:
            provideNameList = [x[0] for x in self.localProvides[dep]]
            # normally, there is only one name in provideNameList

            foundCandidates = set()
            for name in provideNameList:
                for candidate in self.providesNames(name):
                    if self.db.hasTroveByName(candidate):
                        foundCandidates.add(candidate)
                        break
            foundCandidates -= self.compExceptions

            missingCandidates = foundCandidates - self.truncatedBuildRequires
            if missingCandidates == foundCandidates:
                # None of the troves that provides this requirement is
                # reflected in the buildRequires list.  Add candidates
                # to proper list to print at the end:
                if len(foundCandidates) > 1:
                    found = False
                    for candidateSet in missingBuildRequiresChoices:
                        if candidateSet == foundCandidates:
                            found = True
                    if found == False:
                        missingBuildRequiresChoices.append(foundCandidates)
                else:
                    missingBuildRequires.update(foundCandidates)

                # Now give lots of specific information to help the packager
                # in case things do not look so obvious...
                pathList = []
                for path in pathMap:
                    pkgfile = pathMap[path]
                    if pkgfile.hasContents and (pkgfile.requires() & dep):
                        pathList.append(path)
                        l = pathReqMap.setdefault(path, [])
                        l.append(dep)
                if pathList:
                    self.warn('buildRequires %s needed to satisfy "%s"'
                              ' for files: %s',
                              str(sorted(list(foundCandidates))),
                              str(dep),
                              ', '.join(sorted(pathList)))

        if pathReqMap:
            for path in pathReqMap:
                self.warn('file %s has unsatisfied build requirements "%s"',
                          path, '", "'.join([
                             str(x) for x in
                               sorted(list(set(pathReqMap[path])))]))

        if missingBuildRequires:
            self.talk('add to buildRequires: %s',
                       str(sorted(list(set(missingBuildRequires)))))
        if missingBuildRequiresChoices:
            for candidateSet in missingBuildRequiresChoices:
                self.talk('add to buildRequires one of: %s',
                           str(sorted(list(candidateSet))))
        if self.unprovided:
            self.talk('The following dependencies are not resolved'
                      ' within the package or in the system database: %s',
                      str(sorted([str(x) for x in self.unprovided])))

    def providesNames(self, libname):
        return [libname]


class EnforceSonameBuildRequirements(_enforceBuildRequirements):
    """
    NAME
    ====

    B{C{r.EnforceSonameBuildRequirements()}} - Ensure package requires
    dependencies match elements in r.buildRequires list
    
    SYNOPSIS
    ========

    C{r.EnforceSonameBuildRequirements([I{filterexp}] || [I{exceptions='I{pkg}:I{comp}'}])}

    DESCRIPTION
    ===========

    The pluggable policy class C{r.EnforceSonameBuildRequirements()} is
    typically called from within a Conary recipe to ensure that each requires
    dependency in the package is matched by a suitable element in the
    C{buildRequires} list
    
    Any trove names wrongly suggested can be eliminated from the
    list with C{r.EnforceSonameBuildRequirements(exceptions='I{pkg}:I{comp}')}
    
    EXAMPLES
    ========
    
    FIXME NEED EXAMPLE
    """

    depClassType = deps.DEP_CLASS_SONAME
    depClass = deps.SonameDependencies

    def providesNames(self, libname):
        # Instead of requiring the :lib component that satisfies
        # the dependency, our first choice, if possible, is to
        # require :devel, because that would include header files;
        # if it does not exist, then :devellib for a soname link;
        # finally if neither of those exists, then :lib (though
        # that is a degenerate case).
        return [libname.replace(':lib', ':devel'),
                libname.replace(':lib', ':devellib'),
                libname]


class EnforcePythonBuildRequirements(_enforceBuildRequirements):
    """
    NAME
    ====

    B{C{r.EnforcePythonBuildRequirements()}} - Ensure package meets Python
    runtime requirments
    
    SYNOPSIS
    ========

    C{r.EnforcePythonBuildRequirements([I{filterexp}] || [I{exceptions='I{pkg}:I{comp}'}])}

    DESCRIPTION
    ===========

    The pluggable policy class C{r.EnforcePythonBuildRequirements()} is
    typically called from within a Conary recipe to ensure that Python runtime
    requirements are met by the package, or by components listed in the
    C{buildRequires} list.
    
    Any trove names wrongly suggested can be eliminated from the
    list with C{r.EnforcePythonBuildRequirements(exceptions='I{pkg}:I{comp}')}.
    
    EXAMPLES
    ========
    
    FIXME NEED EXAMPLE.
    """

    depClassType = deps.DEP_CLASS_PYTHON
    depClass = deps.PythonDependencies

    # FIXME: remove this when we are ready to enforce Python dependencies
    def setTalk(self):
        self.talk = self.warn


class EnforceJavaBuildRequirements(_enforceBuildRequirements):
    """
    NAME
    ====

    B{C{r.EnforceJavaBuildRequirements()}} - Ensure package meets Java
    runtime requirements
    
    SYNOPSIS
    ========

    C{r.EnforceJavaBuildRequirements([I{filterexp}] || [I{exceptions='I{pkg}:I{comp}'}])}

    DESCRIPTION
    ===========

    The pluggable policy class C{r.EnforceJavaBuildRequirements()} is
    typically called from within a Conary recipe to ensure that Java runtime
    requirements are met by the package, or by components listed in the
    C{buildRequires} list.
    
    Any trove names wrongly suggested can be eliminated from the
    list with C{r.EnforceJavaBuildRequirements(exceptions='I{pkg}:I{comp}')}.
    
    EXAMPLES
    ========
    
    FIXME NEED EXAMPLE
    """

    depClassType = deps.DEP_CLASS_JAVA
    depClass = deps.JavaDependencies

    # FIXME: remove this when we are ready to enforce Java dependencies
    def setTalk(self):
        self.talk = self.warn


class EnforceCILBuildRequirements(_enforceBuildRequirements):
    """
    NAME
    ====

    B{C{r.EnforceCILBuildRequirements()}} - Ensure package meets CIL
    runtime requirements
    
    SYNOPSIS
    ========

    C{r.EnforceCILBuildRequirements([I{filterexp}] || [I{exceptions='I{pkg}:I{comp}'}])}

    DESCRIPTION
    ===========

    The pluggable policy class C{r.EnforceCILBuildRequirements()} is
    typically called from within a Conary recipe to ensure that CIL runtime
    requirements are met by the package, or by components listed in the
    C{buildRequires} list.
    
    Any trove names wrongly suggested can be eliminated from the
    list with C{r.EnforceJavaBuildRequirements(exceptions='I{pkg}:I{comp}')}.
    
    EXAMPLES
    ========
    
    FIXME NEED EXAMPLE
    """

    depClassType = deps.DEP_CLASS_CIL
    depClass = deps.CILDependencies


class EnforcePerlBuildRequirements(_enforceBuildRequirements):
    """
    NAME
    ====

    B{C{r.EnforcePerlBuildRequirements()}} - Ensure package meets Perl
    runtime requirements
    
    SYNOPSIS
    ========

    C{r.EnforcePerlBuildRequirements([I{filterexp}] || [I{exceptions='I{pkg}:I{comp}'}])}

    DESCRIPTION
    ===========

    The pluggable policy class C{r.EnforcePerlBuildRequirements()} is
    typically called from within a Conary recipe to ensure that Perl runtime
    requirements are met by the package, or by components listed in the
    C{buildRequires} list.
    
    Any trove names wrongly suggested can be eliminated from the
    list with C{r.EnforceJavaBuildRequirements(exceptions='I{pkg}:I{comp}')}.
    
    EXAMPLES
    ========
    
    FIXME NEED EXAMPLE
    """

    depClassType = deps.DEP_CLASS_PERL
    depClass = deps.PerlDependencies

    # FIXME: remove this when we are ready to enforce Perl dependencies
    def setTalk(self):
        self.talk = self.warn


class EnforceConfigLogBuildRequirements(policy.EnforcementPolicy):
    """
    NAME
    ====

    B{C{r.EnforcePerlBuildRequirements()}} - Ensures components mentioned in
    config.log files are list as build requirements
    
    SYNOPSIS
    ========

    C{r.EnforcePerlBuildRequirements([I{filterexp}] || [I{/path/to/file/found}] || [I{exceptions='I{pkg}:I{comp}'}])}

    DESCRIPTION
    ===========

    The pluggable policy class C{r.EnforcePerlBuildRequirements()} is
    typically called from within a Conary recipe to ensure components containing
    files mentioned in config.log files are listed as build requirements.
    
    EXAMPLES
    ========
    
    FIXME NEED EXAMPLE
    """
    filetree = policy.BUILDDIR
    invariantinclusions = [ (r'.*/config\.log', 0400, stat.S_IFDIR), ]
    # list of regular expressions (using macros) that cause an
    # entry to be ignored unless a related strings is found in
    # another named file (empty tuple is unconditional blacklist)
    greylist = [
        # config.log string, ((filename, regexp), ...)
        ('%(prefix)s/X11R6/bin/makedepend', ()),
        ('%(bindir)s/g77',
            (('configure.ac', r'\s*AC_PROG_F77'),
             ('configure.in', r'\s*AC_PROG_F77'))),
        ('%(bindir)s/bison',
            (('configure.ac', r'\s*AC_PROC_YACC'),
             ('configure.in', r'\s*(AC_PROG_YACC|YACC=)'))),
    ]

    def test(self):
        return not self.recipe.ignoreDeps

    def preProcess(self):
        self.foundRe = re.compile('^[^ ]+: found (/([^ ]+)?bin/[^ ]+)\n$')
        self.foundPaths = set()
        self.greydict = {}
        # turn list into dictionary, interpolate macros, and compile regexps
        for greyTup in self.greylist:
            self.greydict[greyTup[0] % self.macros] = (
                (x, re.compile(y % self.macros)) for x, y in greyTup[1])
        # process exceptions differently; user can specify either the
        # source (found path) or destination (found component) to ignore
        self.pathExceptions = set()
        self.compExceptions = set()
        if self.exceptions:
            for exception in self.exceptions:
                exception = exception % self.recipe.macros
                if '/' in exception:
                    self.pathExceptions.add(exception)
                else:
                    self.compExceptions.add(exception)
        # never suggest a recursive buildRequires
        self.compExceptions.update(set(self.recipe.autopkg.components.keys()))
        self.exceptions = None

    def foundPath(self, line):
        match = self.foundRe.match(line)
        if match:
            return match.group(1)
        return False

    def doFile(self, path):
        fullpath = self.macros.builddir + path
        # iterator to avoid reading in the whole file at once;
        # nested iterators to avoid matching regexp twice
        foundPaths = set(path for path in 
           (self.foundPath(line) for line in file(fullpath))
           if path and path not in self.pathExceptions)

        # now remove false positives using the greylist
        # copy() for copy because modified
        for foundPath in foundPaths.copy():
            if foundPath in self.greydict:
                foundMatch = False
                for otherFile, testRe in self.greydict[foundPath]:
                    otherFile = fullpath.replace('config.log', otherFile)
                    if not foundMatch and os.path.exists(otherFile):
                        otherFile = file(otherFile)
                        if [line for line in otherFile if testRe.match(line)]:
                            foundMatch = True
                if not foundMatch:
                    # greylist entry has no match, so this is a false
                    # positive and needs to be removed from the set
                    foundPaths.remove(foundPath)
        self.foundPaths.update(foundPaths)

    def postProcess(self):
        if not self.foundPaths:
            return
        # first, get all the trove names in the transitive buildRequires
        # runtime dependency closure
        db = database.Database(self.recipe.cfg.root, self.recipe.cfg.dbPath)
        transitiveBuildRequires = set(
            self.recipe.buildReqMap[spec].getName()
            for spec in self.recipe.buildRequires)
        depSetList = [ self.recipe.buildReqMap[spec].getRequires()
                       for spec in self.recipe.buildRequires ]
        d = db.getTransitiveProvidesClosure(depSetList)
        for depSet in d:
            transitiveBuildRequires.update(set(tup[0] for tup in d[depSet]))

        # next, for each file found, report if it is not in the
        # transitive closure of runtime requirements of buildRequires
        fileReqs = set()
        for path in sorted(self.foundPaths):
            thisFileReqs = set(trove.getName()
                               for trove in db.iterTrovesByPath(path))
            thisFileReqs -= self.compExceptions
            missingReqs = thisFileReqs - transitiveBuildRequires
            if missingReqs:
                self.warn('path %s suggests buildRequires: %s',
                          path, ', '.join((sorted(list(missingReqs)))))
            fileReqs.update(thisFileReqs)

        # finally, give the coalesced suggestion for cut and paste
        # into the recipe if all the individual messages make sense
        missingReqs = fileReqs - transitiveBuildRequires
        if missingReqs:
            self.warn('Probably add to buildRequires: %s',
                      str(sorted(list(missingReqs))))
