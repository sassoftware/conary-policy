#
# Copyright (c) 2009 rPath, Inc.
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

from conary.build import policy, use
from conary.deps import deps

class RemoveBootstrapTroveDependencies(policy.PackagePolicy):
    filetree = policy.PACKAGE
    # must run after all policies that might add a trove: dependency
    requires = (
        ('Requires', policy.REQUIRED_PRIOR),
        ('Provides', policy.REQUIRED_PRIOR),
        ('ComponentProvides', policy.REQUIRED_PRIOR),
        ('EggRequires', policy.CONDITIONAL_PRIOR),
        ('PHPRequires', policy.CONDITIONAL_PRIOR),
        ('PkgConfigRequires', policy.CONDITIONAL_PRIOR),
        ('SymlinkTargetRequires', policy.CONDITIONAL_PRIOR),
        ('XinetdConfigRequires', policy.CONDITIONAL_PRIOR),
    )

    def test(self):
        # This policy is invoked only in the bootstrap case, but should
        # only set the "bootstrap" flavor if it actually makes a change.
        # flag._get() gets value without causing access to be tracked.
        return use.Use.bootstrap._get()

    def do(self):
        components = self.recipe.autopkg.getComponents()
        componentNames = set(x.getName() for x in components)
        for cmp in components:
            removed = False
            depSet = deps.DependencySet()
            for depClass, dep in cmp.requires.iterDeps():
                depName = depClass.tagName
                if depName == 'trove' and str(dep) not in componentNames:
                    self.info("removing 'trove: %s' for bootstrap flavor", dep)
                    removed = True
                    # record bootstrap flavor
                    if use.Use.bootstrap:
                        pass
                else:
                    depSet.addDep(depClass, dep)
            if removed:
                cmp.requires = depSet
