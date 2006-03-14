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

    The pluggable policy class C{r.EtcConfig()} is a deprecated class,
    included only for backwards compatibility.  Use C{r.Config} instead.
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

    The pluggable policy class C{r.InstallBucket()} is a stub class,
    included only for backwards compatibility, and should be removed from use
    in recipes.
    """
    def updateArgs(self, *args, **keywords):
        self.warn('Install buckets are deprecated')

    def test(self):
        return False


class User(policy.EnforcementPolicy):
    """
    NAME
    ====

    B{C{r.User()}} - STUB CLASS
    
    SYNOPSIS
    ========

    Do not use

    DESCRIPTION
    ===========

    The pluggable policy class C{r.User()} is a stub class,
    included only for backwards compatibility, and should be removed from use
    in recipes.
    """
    def updateArgs(self, *args, **keywords):
        self.warn('User policy is deprecated, create a separate UserInfoRecipe instead')

    def test(self):
        return False


class SupplementalGroup(policy.EnforcementPolicy):
    """
    NAME
    ====

    B{C{r.User()}} - STUB CLASS
    
    SYNOPSIS
    ========

    Do not use

    DESCRIPTION
    ===========

    The pluggable policy class C{r.SupplementalGroup()} is a stub class,
    included only for backwards compatibility, and should be removed from use
    in recipes.
    """
    def updateArgs(self, *args, **keywords):
        self.warn('SupplementalGroup policy is deprecated, create a separate GroupInfoRecipe instead')

    def test(self):
        return False


class Group(policy.EnforcementPolicy):
    """
    NAME
    ====

    B{C{r.Group()}} - STUB CLASS
    
    SYNOPSIS
    ========

    Do not use

    DESCRIPTION
    ===========

    The pluggable policy class C{r.Group()} is a stub class,
    included only for backwards compatibility, and should be removed from use
    in recipes.
    """
    def updateArgs(self, *args, **keywords):
        self.warn('Group policy is deprecated, create a separate GroupInfoRecipe instead')

    def test(self):
        return False
