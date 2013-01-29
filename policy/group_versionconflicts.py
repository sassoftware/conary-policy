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


from conary.build import policy

# copied from pkgconfig.py
if hasattr(policy, 'ImageGroupEnforcementPolicy'):
    _ImageGroupEnforcementPolicy = policy.ImageGroupEnforcementPolicy
else:
    # Older Conary. Make the class inherit from object; this policy
    # will then be ignored.
    _ImageGroupEnforcementPolicy = object


class VersionConflicts(_ImageGroupEnforcementPolicy):
    """
    NAME
    ====

    B{C{r.VersionConflicts()}} - Prevents multiple versions of a trove from
    the same branch from being cooked into a group.

    SYNOPSIS
    ========

    C{r.VersionConflicts([I{filterexp}] || [I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The C{r.VersionConflicts} policy enforces that two troves with different
    versions cannot come from the same branch. This situation commonly occurs
    when the current group consumes an upstream group, and they both refer to
    a trove without being explicit about the version to use.

    If an inclusion of exception is passed as a string, it will be converted
    to a trove filter object, treating the string as the name regexp. Trove
    filters can be combined with boolean algebra or bitwise logical operators.

    This policy is an image group policy. Please see GroupRecipe for more
    information.

    EXAMPLES
    ==========

    r.VersionConflicts(exceptions = 'foo')

    Any trove named exactly foo will be ignored for this policy.

    r.VersionConflicts(exceptions = 'group-compat32')

    Any trove inside of group-compat32 will be ignored for this policy.

    fooFilter = r.troveFilter('foo.*', version = 'foo.rpath.org@rpl:1')
    groupFilter = r.troveFilter('group-core')
    r.VersionConflicts(exceptions = fooFilter & groupFilter)

    Any trove that starts with foo on the foo.rpath.org@rpl:1 label in
    group-core will be ignored.

    fooFilter = r.troveFilter('foo.*', flavor = 'is: x86')
    groupFilter = r.troveFilter('group-core')
    r.VersionConflicts(exceptions = fooFilter & -groupFilter)

    Any trove in group-core that does not match fooFilter will be ignored for
    this policy. Effectively this means that foo[is: x86] will be considered,
    but no other trove in group-core.
    """
    def __init__(self, *args, **kwargs):
        self.conflicts = {}
        policy.ImageGroupEnforcementPolicy.__init__(self, *args, **kwargs)

    def doTroveSet(self, troveSet):
        seen = {}
        for trovePath, byDefault, isStrong in troveSet:
            nvf = trovePath[-1]
            if ":" not in nvf[0]:
                # we have to skip packages because they're always present if a
                # component is. if we don't we'll flag excluded components.
                continue
            pkgName = nvf[0].split(':')[0]
            pkgPath = trovePath[:-1]
            id = (pkgName, nvf[1].trailingLabel())
            if id in seen:
                otherPaths = seen[id]
                for otherPath in otherPaths:
                    otherNvf = otherPath[-1]
                    if otherNvf[1] != nvf[1]:
                        existingConflicts = self.conflicts.setdefault(id, [])
                        if otherPath not in existingConflicts:
                            existingConflicts.append(otherPath)
                        if pkgPath not in existingConflicts:
                            existingConflicts.append(trovePath)
            else:
                seen[id] = []
            seen[id].append(trovePath)

    def postProcess(self):
        if self.conflicts:
            allTroves = set()
            for id, paths in self.conflicts.iteritems():
                errorMessage = \
                        "Multiple versions of %s from %s were found:\n\n" % id
                for path in paths:
                    errorMessage += self.formatTrovePath(path) + '\n'
                    allTroves.add(path[-1][0])
                self.recipe.reportErrors(errorMessage[:-1])
            errorMessage = "Multiple versions of these troves were found:"
            errorMessage += '\n' + '\n'.join(sorted(allTroves))
            self.recipe.reportErrors(errorMessage)
