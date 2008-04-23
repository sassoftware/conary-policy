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

import os
import stat

from conary.lib import util
from conary.build import policy


class NonBinariesInBindirs(policy.EnforcementPolicy):
    """
    NAME
    ====

    B{C{r.NonBinariesInBindirs()}} - Enforces executable bits on files in
    binary directories

    SYNOPSIS
    ========

    C{r.NonBinariesInBindirs([I{filterexp}] || [I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The C{r.NonBinariesInBindirs()} policy ensures that files residing in
    directories which are explicitly for binary files have some executable
    bit set.

    EXAMPLES
    ========

    C{r.NonBinariesInBindirs(exceptions='.*')}

    Uses C{r.NonBinariesInBindirs} to except all files in the destination
    directory from the requirement to have executable bits set on them.
    """
    processUnmodified = False
    invariantexceptions = [ ('.*', stat.S_IFDIR) ]
    invariantsubtrees = [
	'%(bindir)s/',
	'%(essentialbindir)s/',
	'%(krbprefix)s/bin/',
	'%(x11prefix)s/bin/',
	'%(sbindir)s/',
	'%(essentialsbindir)s/',
	'%(initdir)s/',
	'%(libexecdir)s/',
	'%(sysconfdir)s/profile.d/',
	'%(sysconfdir)s/cron.daily/',
	'%(sysconfdir)s/cron.hourly/',
	'%(sysconfdir)s/cron.weekly/',
	'%(sysconfdir)s/cron.monthly/',
    ]

    def doFile(self, file):
	d = self.macros['destdir']
	mode = os.lstat(util.joinPaths(d, file))[stat.ST_MODE]
	if not mode & 0111:
            self.error(
                "%s has mode 0%o with no executable permission in bindir",
                file, mode)
	m = self.recipe.magic[file]
	if m and m.name == 'ltwrapper':
            self.error("%s is a build-only libtool wrapper script", file)


class FilesInMandir(policy.EnforcementPolicy):
    """
    NAME
    ====

    B{C{r.FilesInMandir()}} - Enforces man pages being added to
    section directories

    SYNOPSIS
    ========

    C{r.FilesInMandir([I{filterexp}] || [I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The C{r.FilesInMandir()}  policy ensures that system manual page
    directories contain only other directories, and not files,
    so that manual pages are installed into specific sections where
    the C{man} command will find them.

    The main cause of files in C{%(mandir)s} is confusion in packages
    about whether C{%(mandir)s} means /usr/share/man or
    (for example) /usr/share/man/man1.
    """
    processUnmodified = False
    invariantsubtrees = [
        '%(mandir)s',
        '%(x11prefix)s/man',
        '%(krbprefix)s/man',
    ]
    invariantinclusions = [
	(r'.*', None, stat.S_IFDIR),
    ]
    recursive = False

    def doFile(self, file):
        self.error("%s is non-directory file in mandir", file)


class FixupManpagePaths(policy.DestdirPolicy, FilesInMandir):
    """
    NAME
    ====

    B{C{r.FixupManpagePaths()}} - Tries to fix up manpage paths normally caught
    by FilesInMandir, and other mishaps.

    SYNOPSIS
    ========

    C{r.FixupManpagePaths([I{filterexp}] || [I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The C{r.FixupManpagePaths()}  policy ensures that system manual page
    directories contain only other directories, and not files,
    so that manual pages are installed into specific sections where
    the C{man} command will find them.  Handles only man pages with
    integer section names.
    """
    requires = (
        ('FixObsoletePaths', policy.REQUIRED_PRIOR),
        ('NormalizeManPages', policy.CONDITIONAL_SUBSEQUENT),
    )
    processUnmodified = False

    invariantinclusions = [ ('.*', None, stat.S_IFDIR), ]

    invariantsubtrees = []
    for x in '0123456789':
        for y in FilesInMandir.invariantsubtrees:
            invariantsubtrees.append(y+'/'+x)
    invariantsubtrees += FilesInMandir.invariantsubtrees
    invariantinclusions = FilesInMandir.invariantinclusions
    recursive = FilesInMandir.recursive
    
    def logError(self, path):
        self.error('Could not choose correct location for file %s.', path)

    def doFile(self, path):
        # heuristic parsing of a manpage filename to figure out its catagory
        mandir = self.recipe.macros.mandir
        d = self.recipe.macros.destdir
        basename = os.path.basename(path)

        stripped = basename
        if basename.endswith('.gz'):
            stripped =  basename.split('.', 2)[-2]

        if '.' not in stripped:
            self.logError(path)
            return

        num = stripped.split('.', 2)[-1]
        if len(num) > 1 or not num.isdigit():
            self.logError(path)
            return

        newPath = util.joinPaths(d, mandir, 'man'+num, basename)
        self.warn('Moving %s to %s', path, newPath)
        os.renames(d+path, newPath)
        try:
            self.recipe.recordMove(d + path, newPath)
        except AttributeError:
            pass


class BadInterpreterPaths(policy.EnforcementPolicy):
    """
    NAME
    ====

    B{C{r.BadInterpreterPaths()}} - Enforces absolute interpreter paths

    SYNOPSIS
    ========

    C{r.BadInterpreterPaths([I{filterexp}] || [I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The C{r.BadInterpreterPaths()} policy ensures that all paths referring
    to an interpreter instance are absolute, and not relative paths.

    No exceptions to this policy should occur outside of C{%(thisdocdir)s},
    and C{%(thisdocdir)s} is implicitly ignored by this policy.
    """
    processUnmodified = False
    invariantexceptions = [ '%(thisdocdir.literalRegex)s/', ]

    def doFile(self, path):
	d = self.macros['destdir']
	mode = os.lstat(util.joinPaths(d, path))[stat.ST_MODE]
	if not mode & 0111:
            # we care about interpreter paths only in executable scripts
            return
        m = self.recipe.magic[path]
	if m and m.name == 'script':
            interp = m.contents['interpreter']
            if not interp:
                self.error(
                    'missing interpreter in "%s", missing buildRequires?',
                    path)
            elif interp[0] != '/':
                self.error(
                    "illegal relative interpreter path %s in %s (%s)",
                    interp, path, m.contents['line'])


class ImproperlyShared(policy.EnforcementPolicy):
    """
    NAME
    ====

    B{C{r.ImproperlyShared()}} - Enforces shared data directory content

    SYNOPSIS
    ========

    C{r.ImproperlyShared([I{filterexp}] || [I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The C{r.ImproperlyShared()} policy ensures that the C{%(datadir)s}
    directory, (normally C{/usr/share}) contains data which can be shared
    between architectures.

    Architecture-specific files, such as ELF files should not reside in
    C{%(datadir)s}.

    EXAMPLES
    ========

    C{r.ImproperlyShared(exceptions='%(datadir)s/.*')}

    The contents of C{%(datadir)s} are excepted from the policy, allowing
    architecture-dependent data.  (This might be done in a package which
    contains files which are not used directly, but rather used in other
    contexts; for example, binary files interpreted only by emulators.)
    """
    processUnmodified = False
    invariantsubtrees = [ '/usr/share/' ]

    def doFile(self, file):
        m = self.recipe.magic[file]
	if m:
	    if m.name == "ELF":
                self.error(
                    "Architecture-specific file %s in shared data directory",
                    file)
	    if m.name == "ar":
                self.error("Possibly architecture-specific file %s in shared data directory", file)


class CheckDesktopFiles(policy.EnforcementPolicy):
    """
    NAME
    ====

    B{C{r.CheckDesktopFiles()}} - Warns about possible errors in desktop files

    SYNOPSIS
    ========

    C{r.CheckDesktopFiles([I{filterexp}] || [I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The C{r.CheckDesktopFiles()} policy warns about possible errors in
    desktop files, such as missing icon files.

    Use C{r.CheckDesktopFiles} to search for desktop icon files in the
    directories C{%(destdir)s/%(datadir)s} and C{%(datadir)s/icons}.

    You can add additional directories (which will be searched both within
    C{%(destdir)s} and relative to C{/}) with
    C{CheckDesktopFiles(iconDirs='I{/path/to/dir}')} or
    C{CheckDesktopFiles(iconDirs=('I{/path/to/dir1}', 'I{/path/to/dir2}'))}

    EXAMPLES
    ========

    C{r.CheckDesktopFiles(exceptions='%(datadir)s/applications/')}

    Specifies that an element of the package provides an icon in some way
    through the directory named in the exceptions filter expression
    (C{%(datadir)s/applications}).
    """
    processUnmodified = False
    invariantsubtrees = [ '%(datadir)s/applications/' ]
    invariantinclusions = [ r'.*\.desktop' ]

    def __init__(self, *args, **keywords):
        self.iconDirs = [ '%(datadir)s/icons/', '%(datadir)s/pixmaps/' ]
	policy.EnforcementPolicy.__init__(self, *args, **keywords)

    def updateArgs(self, *args, **keywords):
        if 'iconDirs' in keywords:
            iconDirs = keywords.pop('iconDirs')
            if type(iconDirs) in (list, tuple):
                self.iconDirs.extend(iconDirs)
            else:
                self.iconDirs.append(iconDirs)
        policy.EnforcementPolicy.updateArgs(self, *args, **keywords)

    def doFile(self, filename):
        self.iconDirs = [ x % self.macros for x in self.iconDirs ]
        self.checkIcon(filename)

    def checkIcon(self, filename):
        fullname = self.macros.destdir + '/' + filename
        iconfiles = [x.split('=', 1)[1].strip()
                     for x in file(fullname).readlines()
                     if x.startswith('Icon=')]
        for iconfilename in iconfiles:
            # if the .desktop file says "Icon=", ignore it
            if not iconfilename:
                continue
            if iconfilename.startswith('/'):
                fulliconfilename = self.macros.destdir + '/' + iconfilename
                if (not os.path.exists(fulliconfilename) and
                    not os.path.exists(iconfilename)):
                    self.warn('%s says Icon=%s must exist, but is missing',
                               filename, iconfilename)
            elif '/' in iconfilename:
                self.error('Illegal relative path Icon=%s in %s',
                           iconfilename, filename)
            else:
                ext = '.' in iconfilename
                fulldatadir = self.macros.destdir + '/' + self.macros.datadir
                for iconDir in [ fulldatadir ] + self.iconDirs:
                    for root, dirs, files in os.walk(iconDir):
                        if ext:
                            if iconfilename in files:
                                return
                        else:
                            if [ x for x in files
                                 if x.startswith(iconfilename+'.') ]:
                                return
                # didn't find anything
                self.warn('%s says Icon=%s must exist, but it does not exist'
                           ' anywhere in: %s',
                           filename, iconfilename,
                           " ".join([ self.macros.datadir ] + self.iconDirs))


class RequireChkconfig(policy.EnforcementPolicy):
    """
    NAME
    ====

    B{C{r.RequireChkconfig()}} - Require all init scripts provide chkconfig
    information

    SYNOPSIS
    ========

    C{r.RequireChkconfig([I{filterexp}] || [I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The C{r.RequireChkconfig()} policy requires that all init scripts provide
    chkconfig information.

    The only exceptions should be core init scripts, such as reboot.

    EXAMPLES
    ========

    C{r.RequireChkconfig(exceptions='%(initdir)s/halt')}

    Specifies a core init script, C{%(initdir)s/halt} as an exception to the
    policy.
    """
    processUnmodified = False
    invariantsubtrees = [ '%(initdir)s' ]
    def doFile(self, path):
	d = self.macros.destdir
        fullpath = util.joinPaths(d, path)
	if not (os.path.isfile(fullpath) and util.isregular(fullpath)):
            return
        f = file(fullpath)
        lines = f.readlines()
        f.close()
        foundChkconfig = False
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if not line.startswith('#'):
                # chkconfig tag must come before any uncommented lines
                break
            if line.find('chkconfig:') != -1:
                foundChkconfig = True
                break
        if not foundChkconfig:
            self.error("initscript %s must contain chkconfig information before any uncommented lines", path)
