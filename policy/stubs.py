#
# Copyright (c) 2005-2006 rPath, Inc.
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
