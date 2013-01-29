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

from conary.build import packagepolicy
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
