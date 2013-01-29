#
# Copyright (c) SAS Institute Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
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
