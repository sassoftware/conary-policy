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
