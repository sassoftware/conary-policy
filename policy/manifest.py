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

import os

from conary.lib import util
from conary.build import policy


class ParseManifest(policy.PackagePolicy):
    """
    NAME
    ====

    B{C{r.ParseManifest()}} - Parses a file containing a manifest intended for
    RPM

    SYNOPSIS
    ========

    C{r.ParseManifest([I{filterexp}])}

    DESCRIPTION
    ===========

    The C{r.ParseManifest()} policy parses a file containing a manifest
    intended for RPM

    In the manifest, C{r.ParseManifest()} finds the information that cannot
    be represented by pure filesystem status with non-root built device files,
    (C{%dev}) and permissions (C{%attr}).

    It ignores directory ownership (C{%dir}) because Conary handles
    directories very differently from RPM.

    The class C{r.ParseManifest} also ignores C{%defattr} because Conary's
    default ownership is C{root:root}, and because permissions
    (except for setuid and setgid files) are collected from the filesystem.

    C{r.ParseManifest} translates each parsed manifest line, into the related
    Conary construct.

    Warning: tested only with MAKEDEV output so far.
    """

    requires = (
        ('setModes', policy.REQUIRED),
        ('MakeDevices', policy.REQUIRED),
        ('Ownership', policy.REQUIRED),
    )
    processUnmodified = False

    def __init__(self, *args, **keywords):
	self.paths = []
	policy.PackagePolicy.__init__(self, *args, **keywords)

    def updateArgs(self, *args, **keywords):
	"""
	ParseManifest(path(s)...)
	"""
	if args:
	    self.paths.extend(args)
	policy.PackagePolicy.updateArgs(self, **keywords)

    def do(self):
	for path in self.paths:
	    self.processPath(path)

    def processPath(self, path):
        import epdb; epdb.st()
	if not path.startswith('/'):
	    path = self.macros['builddir'] + os.sep + path
        f = open(path)
        for line in f:
            line = line.strip()
            fields = line.split(')')

            attr = fields[0].lstrip('%attr(').split(',')
            perms = attr[0].strip()
            owner = attr[1].strip()
            group = attr[2].strip()

            fields[1] = fields[1].strip()
            if fields[1].startswith('%dev('):
                dev = fields[1][5:].split(',')
                devtype = dev[0]
                major = dev[1]
                minor = dev[2]
                target = fields[2].strip()
                self.recipe.MakeDevices(target, devtype, int(major), int(minor),
                                        owner, group, int(perms, 0))
            elif fields[1].startswith('%dir '):
		pass
		# ignore -- Conary directory handling is too different
		# to map
            else:
		# XXX is this right?
                target = fields[1].strip()
		if int(perms, 0) & 06000:
		    self.recipe.setModes(int(perms, 0),
                                         util.literalRegex(target))
		if owner != 'root' or group != 'root':
		    self.recipe.Ownership(owner, group,
                                          util.literalRegex(target))
