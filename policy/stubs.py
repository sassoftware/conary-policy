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

"""
These policies are stubs to help convert old recipes that reference
obsolete policy.
"""

from conary.build import policy

class EtcConfig(policy.EnforcementPolicy):
    """
    NAME
    ====

    B{C{r.EtcConfig()}} - DEPRECATED CLASS

    SYNOPSIS
    ========

    Do not use

    DESCRIPTION
    ===========

    The C{r.EtcConfig()} class is a deprecated class, included only for
    backwards compatibility.  Use C{r.Config} instead.
    """
    def updateArgs(self, *args, **keywords):
        self.warn('EtcConfig deprecated, please use Config instead')
        self.recipe.Config(*args, **keywords)
    def do(self):
        pass


class InstallBucket(policy.EnforcementPolicy):
    """
    NAME
    ====

    B{C{r.InstallBucket()}} - STUB CLASS

    SYNOPSIS
    ========

    Do not use

    DESCRIPTION
    ===========

    The C{r.InstallBucket()} policy is a stub, included only for backwards
    compatibility, and should be removed from use in recipes.
    """
    def updateArgs(self, *args, **keywords):
        self.warn('Install buckets are deprecated')

    def test(self):
        return False


class ObsoletePaths(policy.EnforcementPolicy):
    """
    NAME
    ====

    B{C{r.ObsoletePaths()}} - Replaced by B{C{r.FixObsoletePaths}}
    """
    def updateArgs(self, *args, **keywords):
        self.warn('ObsoletePaths has been replaced by FixObsoletePaths')

    def test(self):
        return False
