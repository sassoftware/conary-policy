#
# Copyright (c) 2004-2006 rPath, Inc.
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

from conary.build import filter, policy
from conary.deps import deps
from conary.lib import util


class RelativeSymlinks(policy.DestdirPolicy):
    """
   NAME
    ====

    B{C{r.RelativeSymlinks()}} - Create relative symbolic links

    SYNOPSIS
    ========

    C{r.RelativeSymlinks([filterexp])}

    DESCRIPTION
    ===========

    The C{r.RelativeSymlinks()} class is called from within a Conary
    recipe to make symbolic links relative.

    Create absolute symbolic links in your recipes, and C{r.RelativeSymlinks}
    will create minimal relative symbolic links from them

    PARAMETERS
    ==========

    EXAMPLES
    ========

    FIXME NEED EXAMPLE
    """
    def doFile(self, path):
        fullpath = self.macros['destdir']+path
        if os.path.islink(fullpath):
            contents = os.readlink(fullpath)
            if contents.startswith('/'):
                pathlist = util.normpath(path).split('/')
                contentslist = util.normpath(contents).split('/')
                if pathlist == contentslist:
                    raise policy.PolicyError('Symlink points to itself:'
                                             ' %s -> %s' % (path, contents))
                while pathlist[0] == contentslist[0]:
                    pathlist = pathlist[1:]
                    contentslist = contentslist[1:]
                os.remove(fullpath)
                dots = "../"
                dots *= len(pathlist) - 1
                normpath = util.normpath(dots + '/'.join(contentslist))
                os.symlink(normpath, fullpath)


class DanglingSymlinks(policy.PackagePolicy):
    """
    NAME
    ====

    B{C{r.DanglingSymlinks()}} - Disallow dangling symbolic links

    SYNOPSIS
    ========

    C{r.DanglingSymlinks([filterexp] || [I{exceptions=filterexp})}

    DESCRIPTION
    ===========

    The C{r.DanglingSymlinks()} class is called from within a Conary
    recipe to enforce the absence of dangling symbolic links, that is,
    symbolic links point to targets which no longer exist.

    If you know that a dangling symbolic link created by your package
    is fulfilled by another package on which your package depends,
    you may set up an exception for that file.

    PARAMETERS
    ==========

    EXAMPLES
    ========

    FIXME NEED EXAMPLE
    """
    invariantexceptions = (
	'%(testdir)s/.*', )
    targetexceptions = [
        # ('filterexp', 'requirement')
	('.*consolehelper', 'usermode:runtime'),
	('/proc(/.*)?', None), # provided by the kernel, no package
    ]
    def doProcess(self, recipe):
	self.rootdir = self.rootdir % recipe.macros
	self.targetFilters = []
	self.macros = recipe.macros # for filterExpression
	for targetitem, requirement in self.targetexceptions:
	    filterargs = self.filterExpression(targetitem)
	    self.targetFilters.append((filter.Filter(*filterargs), requirement))
	policy.PackagePolicy.doProcess(self, recipe)

    def doFile(self, path):
	d = self.macros.destdir
        l = len(d)
	f = util.joinPaths(d, path)
        recipe = self.recipe
	if os.path.islink(f):
	    contents = os.readlink(f)
	    if contents[0] == '/':
                self.warn('Absolute symlink %s points to %s,'
                          ' should probably be relative', path, contents)
		return
	    abscontents = util.joinPaths(os.path.dirname(path), contents)
            # now resolve any intermediate symlinks
            abscontents = os.path.realpath(d+abscontents)[l:]
            ap = recipe.autopkg
	    if abscontents in ap.pathMap:
		componentMap = ap.componentMap
		if componentMap[abscontents] != componentMap[path] and \
		   not path.endswith('.so') and \
		   not componentMap[path].getName().endswith(':test'):
		    # warn about suspicious cross-component symlink
                    fromPkg = ap.componentMap[path]
                    targetPkg = ap.componentMap[abscontents]

                    found = False
                    for depClass, dep in fromPkg.requires.iterDeps():
                        d = deps.DependencySet()
                        d.addDep(depClass, dep)
                        if targetPkg.provides.satisfies(d):
                            found = True
                            break

                    if not found:
                        self.warn('symlink %s points from package %s to %s',
                                  path, componentMap[path].getName(),
                                  componentMap[abscontents].getName())
	    else:
		for targetFilter, requirement in self.targetFilters:
		    if targetFilter.match(abscontents):
			# contents are an exception
                        self.info('allowing special dangling symlink %s -> %s',
                                  path, contents)
                        if requirement:
                            self.info('automatically adding requirement'
                                      ' %s for symlink %s', requirement, path)
                            # Requires has already run, touch this up
                            pkg = ap.componentMap[path]
                            if path not in pkg.requiresMap:
                                pkg.requiresMap[path] = deps.DependencySet()
                            pkg.requiresMap[path].addDep(
                                deps.TroveDependencies,
                                deps.Dependency(requirement, []))
                            f = pkg.getFile(path)
                            f.requires.set(pkg.requiresMap[path])
                            pkg.requires.union(f.requires())
			return
                for pathName in recipe.autopkg.pathMap:
                    if pathName.startswith(abscontents):
                        # a link to a subdirectory of a file that is
                        # packaged is still OK; this test is expensive
                        # and almost never needed, so put off till last
                        return
		self.error(
		    "Dangling symlink: %s points to non-existant %s (%s)"
		    %(path, contents, abscontents))
