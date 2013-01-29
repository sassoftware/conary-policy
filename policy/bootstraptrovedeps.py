#
# Copyright (c) rPath, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
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
