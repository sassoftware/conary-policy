#
# Copyright (c) 2004-2006 rPath, Inc.
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

from conary.lib import util
from conary.build import policy, recipe


class RemoveNonPackageFiles(policy.DestdirPolicy):
    """
    NAME
    ====

    B{C{r.RemoveNonPackageFiles()}} - Remove classes of files that should not
    be packaged

    SYNOPSIS
    ========

    C{r.RemoveNonPackageFiles([I{filterexp},] [I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The C{r.RemoveNonPackageFiles()} policy removes classes of files that
    normally should not be packaged.

    EXAMPLES
    ========

    C{r.RemoveNonPackageFiles(exceptions='.*\.la')}

    This is one of the rare packages that requires .la files to be
    installed in order to work.
    """
    requires = (
        ('Strip', policy.CONDITIONAL_PRIOR),
        ('NormalizeManPages', policy.CONDITIONAL_SUBSEQUENT),
        ('NormalizeAppDefaults', policy.CONDITIONAL_SUBSEQUENT),
        ('NormalizeCompression', policy.CONDITIONAL_SUBSEQUENT),
        ('NormalizeInfoPages', policy.CONDITIONAL_SUBSEQUENT),
        ('NormalizeInitscriptLocation', policy.CONDITIONAL_SUBSEQUENT),
        ('NormalizeInitscriptContents', policy.CONDITIONAL_SUBSEQUENT),
        ('NormalizeInterpreterPaths', policy.CONDITIONAL_SUBSEQUENT),
        ('NormalizePamConfig', policy.CONDITIONAL_SUBSEQUENT),
        ('NormalizePkgConfig', policy.CONDITIONAL_SUBSEQUENT),
        ('NormalizePythonInterpreterVersion', policy.CONDITIONAL_SUBSEQUENT),
    )
    processUnmodified = False
    invariantinclusions = [
        r'\.la$',
        # python .a's might have been installed in the wrong place on multilib
        r'%(prefix)s/(lib|%(lib)s)/python.*/site-packages/.*\.a$',
        r'perllocal\.pod$',
        r'\.packlist$',
        r'\.cvsignore$',
        r'\.orig$',
        r'%(sysconfdir)s.*/rc[0-6].d/[KS].*$',
        '~$',
        r'.*/\.#.*',
        '/(var/)?tmp/',
        r'.*/fonts.(cache.*|dir|scale)$',
    ]

    def test(self):
        if hasattr(self.recipe, '_getCapsulePathsForFile'):
            if self.recipe.getType() == recipe.RECIPE_TYPE_CAPSULE:
                return False
        return True

    def doFile(self, path):
        if hasattr(self.recipe, '_getCapsulePathsForFile'):
            if self.recipe._getCapsulePathsForFile(path):
                return
        self.info("Removing %s", path)
        util.remove(self.macros['destdir']+path, quiet=True)
