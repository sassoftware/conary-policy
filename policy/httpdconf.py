#
# Copyright (c) 2008 rPath, Inc.
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

import itertools
import os
import re

from conary.build import policy, packagepolicy
from conary.deps import deps

if hasattr(packagepolicy, '_basePluggableRequires'):
    _basePluggableRequires = packagepolicy._basePluggableRequires
else:
    # Older Conary. Make the class inherit from object; this policy
    # will then be ignored.
    _basePluggableRequires = object

class HttpdConfigRequires(_basePluggableRequires):
    """
    NAME
    ====

    B{C{r.HttpdConfigRequires()}} - Automatically add a requirement of
    C{/usr/sbin/httpd} for packages containing an httpd configuration file.

    SYNOPSIS
    ========

    C{r.HttpdConfigRequires([I{filterexp}] || [I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The C{r.HttpdConfigRequires()} policy adds a requirement of
    C{/usr/sbin/httpd} for packages containing an httpd configuration file.
    It adds this only if the configuration file contains non-empty,
    non-comment lines, so that commented-out example files do not
    generate this dependency.

    This policy is a sub-policy of C{r.Requires}. It inherits
    the list of exceptions from C{r.Requires}. Under normal
    circumstances, it is not necessary to invoke this policy
    explicitly; call C{r.Requires} instead. However, it may be useful
    to exclude some of the files from being scanned only by this
    policy, in which case using I{exceptions=filterexp} is possible.

    EXAMPLES
    ========

    C{r.HttpdConfigRequires(exceptions='foo.conf')}

    Disables adding an /usr/sbin/httpd requirement for the
    C{/etc/httpd/conf.d/foo.conf} file.  This is normally used
    when the configuration file provided is meant only to enable
    web services if the web server is installed, but not if
    a web server is not installed; an additional, optional
    feature.
    """

    invariantinclusions = [ r'%(sysconfdir)s/httpd/conf.d/.*\.conf' ]

    def addPluggableRequirements(self, path, fullpath, pkgFiles, macros):
        # test stripped lines to ignore all leading and trailing whitespace
        # so that indented comments and lines with only whitespace are
        # not counted as having configuration information in them
        conflines = [y for y in (x.strip() for x in file(fullpath).readlines())
                     if y and not y.startswith('#')]
        if not conflines:
            # All lines are blank or commented
            return

        self._addRequirement(path, "/usr/sbin/httpd", [], pkgFiles,
                             deps.FileDependencies)
