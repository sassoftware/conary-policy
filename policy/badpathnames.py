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
import re
import stat

from conary.lib import magic, util
from conary.build import policy, recipe


class BadFilenames(policy.EnforcementPolicy):
    """
    NAME
    ====

    B{C{r.BadFilenames()}} - Require absence of newlines in filenames

    SYNOPSIS
    ========

    C{r.BadFilenames([I{filterexp}])}

    DESCRIPTION
    ===========

    The C{r.BadFilenames()} policy ensures that filenames do not contain
    newlines, as filenames are separated by newlines in several conary
    protocols.

    No exceptions are allowed.
    """
    processUnmodified = True
    def test(self):
        assert(not self.exceptions)
        return True
    def doFile(self, path):
        if path.find('\n') != -1:
            self.error("path %s has illegal newline character", path)


class NonUTF8Filenames(policy.EnforcementPolicy):
    """
    NAME
    ====

    B{C{r.NonUTF8Filenames()}} - Require UTF-8 encoded filenames

    SYNOPSIS
    ========

    C{r.NonUTF8Filenames([I{filterexp}])}

    DESCRIPTION
    ===========

    The C{r.NonUTF8Filenames()} policy requires filenames be encoded in
    UTF-8, as that is the standard encoding.
    """
    processUnmodified = True
    def doFile(self, path):
        if hasattr(self.recipe, '_getCapsulePathsForFile'):
            if self.recipe._getCapsulePathsForFile(path):
                return
        try:
            path.decode('utf-8')
        except UnicodeDecodeError:
            self.error('path "%s" is not valid UTF-8', path)


class NonMultilibComponent(policy.EnforcementPolicy):
    """
    NAME
    ====

    B{C{r.NonMultilibComponent()}} - Enforces multilib support

    SYNOPSIS
    ========

    C{r.NonMultilibComponent([I{filterexp}])}

    DESCRIPTION
    ===========

    The C{r.NonMultilibComponent()} policy enforces multilib support so
    that both 32-bit and 64-bit components may be installed for Python
    and Perl.

    Python and Perl components should generally be under C{/usr/lib}, unless
    they have binaries and are built on a 64-bit platform, in which case
    they should have no files under C{/usr/lib}.
    """
    processUnmodified = False
    invariantsubtrees = [
        '%(libdir)s/',
        '%(prefix)s/lib/',
    ]
    invariantinclusions = [
        '.*/python[^/]*/site-packages/.*',
        '.*/perl[^/]*/vendor-perl/.*',
    ]
    invariantexceptions = [
        '%(debuglibdir)s/',
    ]

    def __init__(self, *args, **keywords):
        self.foundlib = {'python': False, 'perl': False}
        self.foundlib64 = {'python': False, 'perl': False}
        self.reported = {'python': False, 'perl': False}
        self.productMapRe = re.compile(
            '.*/(python|perl)[^/]*/(site-packages|vendor-perl)/.*')
	policy.EnforcementPolicy.__init__(self, *args, **keywords)

    def test(self):
	if self.macros.lib == 'lib':
	    # no need to do anything
	    return False
        return True

    def doFile(self, path):
        if hasattr(self.recipe, '_getCapsulePathsForFile'):
            if self.recipe._getCapsulePathsForFile(path):
                return
        if not False in self.reported.values():
            return
        # we've already matched effectively the same regex, so should match...
        p = self.productMapRe.match(path).group(1)
        if self.reported[p]:
            return
        if os.path.isdir(self.recipe.macros.destdir+path):
            return
        if self.currentsubtree == '%(libdir)s/':
            self.foundlib64[p] = path
        else:
            self.foundlib[p] = path
        if self.foundlib64[p] and self.foundlib[p] and not self.reported[p]:
            self.error(
                '%s packages may install in /usr/lib or /usr/lib64,'
                ' but not both: at least %s and %s both exist',
                p, self.foundlib[p], self.foundlib64[p])
            self.reported[p] = True


class NonMultilibDirectories(policy.EnforcementPolicy):
    """
    NAME
    ====

    B{C{r.NonMultilibDirectories()}} - Enforces platform-specific directory
    names

    SYNOPSIS
    ========

    C{r.NonMultilibDirectories([I{filterexp}])}

    DESCRIPTION
    ===========

    The C{r.NonMultilibDirectories()} policy enforces proper directories
    relevant to platform. Troves for 32-bit platforms should not normally
    contain directories named "C{lib64}".
    """
    processUnmodified = False
    invariantinclusions = [ ( '.*/lib64', stat.S_IFDIR ), ]

    def test(self):
	if self.macros.lib == 'lib64':
	    # no need to do anything
	    return False
        return True

    def doFile(self, path):
        if hasattr(self.recipe, '_getCapsulePathsForFile'):
            if self.recipe._getCapsulePathsForFile(path):
                return
        self.error('path %s has illegal lib64 component on 32-bit platform',
                   path)


class CheckDestDir(policy.EnforcementPolicy):
    """
    NAME
    ====

    B{C{r.CheckDestDir()}} - Enforces absence of destination directory

    SYNOPSIS
    ========

    C{r.CheckDestDir([I{filterexp}])}

    DESCRIPTION
    ===========

    The C{r.CheckDestDir()} policy enforces absence of C{%(destdir)s} path
    in file paths and symbolic link contents.

    The C{%(destdir)s} should not be contained within file paths and symbolic
    link contents.

    Though files should also not contain C{%(destdir)s}, C{r.CheckDestDir}
    does not search inside files.
    """
    processUnmodified = False
    def doFile(self, filename):
        if hasattr(self.recipe, '_getCapsulePathsForFile'):
            if self.recipe._getCapsulePathsForFile(filename):
                return

	d = self.macros.destdir
        b = self.macros.builddir

	if filename.find(d) != -1:
            self.error('Path %s contains destdir %s', filename, d)
	fullpath = d+filename
	if os.path.islink(fullpath):
	    contents = os.readlink(fullpath)
	    if contents.find(d) != -1:
                self.error('Symlink %s contains destdir %s in contents %s',
                           filename, d, contents)
	    if contents.find(b) != -1:
                self.error('Symlink %s contains builddir %s in contents %s',
                           filename, b, contents)

        badRPATHS = (d, b, '/tmp', '/var/tmp')
        m = self.recipe.magic[filename]
        if m and m.name == "ELF":
            rpaths = m.contents['RPATH'] or ''
            for rpath in rpaths.split(':'):
                for badRPATH in badRPATHS:
                    if rpath.startswith(badRPATH):
                        self.error('file %s has illegal RPATH %s', filename, rpath)
                        break


class FilesForDirectories(policy.EnforcementPolicy):
    """
    NAME
    ====

    B{C{r.FilesForDirectories()}} - Warn about files where directories are
    expected

    SYNOPSIS
    ========

    C{r.FilesForDirectories([I{filterexp}])}

    DESCRIPTION
    ===========

    The C{r.FilesForDirectories()} policy warns about encountering files
    where directories are expected. This condition is normally caused by bad
    C{r.Install()} invocations.

    This policy does not honor exceptions.
    """
    # This list represents an attempt to pick the most likely directories
    # to make these mistakes with: directories potentially inhabited by
    # files from multiple packages, with reasonable possibility that they
    # will have files installed by hand rather than by a "make install".
    candidates = (
	'/bin',
	'/sbin',
	'/etc',
	'/etc/X11',
	'/etc/init.d',
	'/etc/sysconfig',
	'/etc/xinetd.d',
	'/lib',
	'/mnt',
	'/opt',
	'/usr',
	'/usr/bin',
	'/usr/sbin',
	'/usr/lib',
	'/usr/libexec',
	'/usr/include',
	'/usr/share',
	'/usr/share/info',
	'/usr/share/man',
	'/usr/share/man/man1',
	'/usr/share/man/man2',
	'/usr/share/man/man3',
	'/usr/share/man/man4',
	'/usr/share/man/man5',
	'/usr/share/man/man6',
	'/usr/share/man/man7',
	'/usr/share/man/man8',
	'/usr/share/man/man9',
	'/usr/share/man/mann',
	'/var/lib',
	'/var/spool',
    )
    processUnmodified = False
    def do(self):
	d = self.recipe.macros.destdir
	for path in self.candidates:
            if hasattr(self.recipe, '_getCapsulePathsForFile'):
                if self.recipe._getCapsulePathsForFile(path):
                    break
	    fullpath = util.joinPaths(d, path)
	    if os.path.exists(fullpath):
		if not os.path.isdir(fullpath):
                    self.error(
                        'File %s should be a directory; bad r.Install()?', path)


class _pathMap(policy.Policy):
    candidates = {}

    def candidatePaths(self):
        d = self.recipe.macros.destdir
        for path in self.candidates.keys():
            fullpath = util.joinPaths(d, path)
            if os.path.exists(fullpath):
                yield (path, self.candidates[path])


class FixObsoletePaths(policy.DestdirPolicy, _pathMap):
    """
    NAME
    ====

    B{C{r.FixObsoletePaths()}} - Attempt to fix obsolete paths

    SYNOPSIS
    ========

    C{r.FixObsoletePaths([I{filterexp}])}

    DESCRIPTION
    ===========

    The C{r.FixObsoletePaths()} policy attempts to correct obsolete 
    paths.

    This policy does not honor exceptions.
    """
    
    requires = (
        ('AutoDoc', policy.REQUIRED_SUBSEQUENT),
    )
    processUnmodified = False

    candidates = {
        '/usr/man': '/usr/share/man',
        '/usr/info': '/usr/share/info',
        '/usr/doc': '/usr/share/doc',
    }

    def do(self):
        if hasattr(self.recipe, '_getCapsulePathsForFile'):
            if self.recipe.getType() == recipe.RECIPE_TYPE_CAPSULE:
                # Cannot reasonably separate capsule and non-capsule
                # paths in this policy, so bail
                return
        d = self.recipe.macros.destdir
        for path, newPath in self.candidatePaths():
            if os.path.isdir(d + path) and not os.listdir(d + path):
                self.warn("Path %s should not exist, but is empty. removing." \
                        % path)
                os.rmdir(d + path)
                continue
            try:
                try:
                    self.recipe.recordMove(d + path, d + newPath)
                except AttributeError:
                    pass
                os.renames(d+path, d+newPath)
                self.warn('Path %s should not exist, moving to %s instead',
                          path, newPath)
            except OSError:
                self.error('Path %s should not exist; attempt to '
                    'move failed. Please move it to %s instead.',
                    path, newPath)


class NonLSBPaths(policy.EnforcementPolicy, _pathMap):
    """
    NAME
    ====

    B{C{r.NonLSBPaths()}} - Warn about non-LSB paths

    SYNOPSIS
    ========

    C{r.NonLSBPaths(exceptions=I{filterexp})}

    DESCRIPTION
    ===========

    This policy warns about paths that conflict with the LSB in some
    way.
    """
    requires = (
        ('ExcludeDirectories', policy.REQUIRED_PRIOR),
    )
    processUnmodified = False
    
    candidates = {
        '/usr/local':
           ('/usr',
            False,
            '/usr/local is recommended by the LSB only for non-packaged files'),
        '/usr/usr':
           ('/usr',
            True,
            '/usr/usr is usually caused by using %(prefix)s instead of /'),
    }

    def doProcess(self, recipe):
        self.invariantinclusions = self.candidates.keys()
        policy.EnforcementPolicy.doProcess(self, recipe)

    def doFile(self, path):
        newPath, error, advice = self.candidates[path]
        if hasattr(self.recipe, '_getCapsulePathsForFile'):
            if self.recipe.getType() == recipe.RECIPE_TYPE_CAPSULE:
                error = False
        if error:
            talk = self.error
        else:
            talk = self.warn
        talk('Found path %s: %s', path, advice)


class PythonEggs(policy.EnforcementPolicy):
    """
    NAME
    ====

    B{C{r.PythonEggs()}} - Enforce absence of Python .egg files

    SYNOPSIS
    ========

    C{r.PythonEggs([I{filterexp}])}

    DESCRIPTION
    ===========

    The C{r.PythonEggs()} policy enforces the absence of Python C{.egg}
    files, which are incompatible with package management.

    Python  packages should be built with the
    C{--single-version-externally-managed} command line argument, in which
    case the C{.egg} files will not be created.
    """
    processUnmodified = False
    invariantinclusions = [
        ('.*/python[^/]*/site-packages/.*\.egg', stat.S_IFREG),
    ]

    def doFile(self, path):
        if hasattr(self.recipe, '_getCapsulePathsForFile'):
            if self.recipe._getCapsulePathsForFile(path):
                return
        fullPath = util.joinPaths(self.recipe.macros.destdir, path)
        m = magic.magic(fullPath)
        if not (m and m.name == 'ZIP'):
            self.error("%s exists but isn't a valid Python .egg", path)
        else:
            self.error('Python .egg %s exists; use'
                       ' --single-version-externally-managed argument'
                       ' to setup.py or use r.PythonSetup()', path)
