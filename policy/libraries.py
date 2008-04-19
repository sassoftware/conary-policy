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
from conary.local import database


# probably needs to migrate to some form of configuration
# need lib and %(lib)s bits for multilib
librarydirs = [
    '%(libdir)s/',
    '%(prefix)s/lib/',
    '%(essentiallibdir)s/',
    '/lib/',
    '%(krbprefix)s/%(lib)s/',
    '%(krbprefix)s/lib/',
    '%(x11prefix)s/%(lib)s/',
    '%(x11prefix)s/lib/',
    '%(prefix)s/local/%(lib)s/',
    '%(prefix)s/local/lib/',
]

class AutoSharedLibrary(policy.DestdirPolicy):
    """
    NAME
    ====

    B{C{r.AutoSharedLibrary()}} - Automatically determine SharedLibrary
    subtrees based on contents of /etc/ld.so.conf.d/*.conf files

    SYNOPSIS
    ========

    C{r.AutoSharedLibrary([I{filterexp}] I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The C{r.AutoSharedLibrary()} policy automatically determines directories
    that should be marked as SharedLibrary based on the contents of
    /etc/ld.so.conf.d/*.conf files. This policy checks system files as well
    as destdir files.

    Note: Do not invoke C{r.AutoSharedLibrary()} directly from recipes.
    If you need to mark a directory as containing shared libraries,
    use r.SharedLibrary.
    """

    requires = (
        ('ExecutableLibraries', policy.CONDITIONAL_SUBSEQUENT),
        ('CheckSonames', policy.CONDITIONAL_SUBSEQUENT),
        ('NormalizeLibrarySymlinks', policy.CONDITIONAL_SUBSEQUENT),
        ('Provides', policy.CONDITIONAL_SUBSEQUENT),
        ('Requires', policy.CONDITIONAL_SUBSEQUENT),
    )

    def _managedFile(self, path):
        db = database.Database(self.recipe.cfg.root, self.recipe.cfg.dbPath)
        return bool(db.iterTrovesByPath(path))

    def _iterSharedlibList(self):
        destdir = self.recipe.macros.destdir
        basePath = os.path.join(os.path.sep, 'etc', 'ld.so.conf.d')
        root = self.recipe.cfg.root
        for checkManaged, ldConfPath in \
                ((True, util.joinPaths(root, basePath)),
                (False, util.joinPaths(destdir, basePath))):
            if not os.path.exists(ldConfPath):
                # if the dir doesn't exist, there's nothing to do
                continue
            for ldConfFile in os.listdir(ldConfPath):
                if not ldConfFile.endswith('.conf'):
                    # skip files that don't end with exactly .conf. A side
                    # effect of this is to prevent checking .conflicts
                    # or backup files.
                    continue
                fullpath = os.path.join(ldConfPath, ldConfFile)
                # skip all unmanaged files if necessary
                if checkManaged and not self._managedFile( \
                        util.joinPaths(basePath, ldConfFile)):
                    continue
                f = open(fullpath)
                for path in f:
                    yield path.strip()

    def doProcess(self, recipe):
        for path in self._iterSharedlibList():
            self.recipe.SharedLibrary(subtrees = path)

class SharedLibrary(policy.PackagePolicy):
    """
    NAME
    ====

    B{C{r.SharedLibrary()}} - Mark system shared libraries

    SYNOPSIS
    ========

    C{r.SharedLibrary([I{filterexp}] || [I{subtrees=path}])}

    DESCRIPTION
    ===========

    The C{r.SharedLibrary()} policy marks system shared libraries such
    that C{ldconfig} will be run.

    C{r.SharedLibrary(subtrees=I{path})} to mark a path as containing
    shared libraries; C{r.SharedLibrary(I{filterexp})} to mark a file.

    C{r.SharedLibrary} does B{not} walk entire directory trees.  Every
    directory that you want to add must be passed in using the
    C{subtrees} keyword.

    EXAMPLES
    ========

    C{r.SharedLibrary(subtrees='%(libdir)s/mysql/')}

    Causes the C{%(libdir)s/mysql/} directory to be considered as a
    source of shared libraries; files in that directory will be marked
    as shared libraries, all appropriate actions will be taken at
    install time, and Conary policies enforcing appropriate practices
    for libraries will be enabled for that directory.
    """
    requires = (
        ('ExecutableLibraries', policy.REQUIRED),
        ('CheckSonames', policy.REQUIRED),
        ('NormalizeLibrarySymlinks', policy.REQUIRED),
        ('Provides', policy.REQUIRED),
        ('Requires', policy.REQUIRED),
    )
    processUnmodified = False

    invariantsubtrees = librarydirs
    invariantinclusions = [
	(r'..*\.so\..*', None, stat.S_IFDIR),
    ]
    recursive = False

    def postInit(self):
        # Provides and Requires need to know about librarydirs
        d = {'sonameSubtrees': librarydirs}
        self.recipe.Provides(**d)
        self.recipe.Requires(**d)

    def updateArgs(self, *args, **keywords):
	policy.PackagePolicy.updateArgs(self, *args, **keywords)
        if 'subtrees' in keywords:
            # share with other policies that need to know about shlibs
            d = {'subtrees': keywords['subtrees']}
            self.recipe.ExecutableLibraries(**d)
            self.recipe.CheckSonames(**d)
            self.recipe.NormalizeLibrarySymlinks(**d)
            # Provides and Requires need this information passed elsewise
            d = {'sonameSubtrees': keywords['subtrees']}
            self.recipe.Provides(**d)
            self.recipe.Requires(**d)

    def doFile(self, filename):
	fullpath = self.macros.destdir + filename
	if os.path.isfile(fullpath) and util.isregular(fullpath):
	    m = self.recipe.magic[filename]
	    if m and m.name == 'ELF' and 'soname' in m.contents:
                self.info(filename)
		self.recipe.autopkg.pathMap[filename].tags.set("shlib")


class FixupMultilibPaths(policy.DestdirPolicy):
    """
    NAME
    ====

    B{C{r.FixupMultilibPaths()}} - Fix up and warn about files installed in directories that do not allow side-by-side installation of multilib-capable libraries

    SYNOPSIS
    ========

    C{r.FixupMultilibPaths([I{filterexp}] I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The C{r.FixupMultilibPaths()} policy fixes up and warns about programs
    which do not know about C{%(lib)s}, and attempt to install to C{lib}
    when they should be installing to C{lib64} instead.

    EXAMPLES
    ========

    C{r.FixupMultilibPaths(exceptions='.*')}

    The package being built is explicitly not multilib-safe, and
    therefore the policy should not run (extremely rare).
    """
    requires = (
        ('ExecutableLibraries', policy.CONDITIONAL_SUBSEQUENT),
        ('Strip', policy.CONDITIONAL_SUBSEQUENT),
    )
    processUnmodified = False
    invariantinclusions = [
        '.*\.(so.*|a)$',
    ]

    def __init__(self, *args, **keywords):
        self.dirmap = {
            '/lib':            '/%(lib)s',
            '%(prefix)s/lib':  '%(libdir)s',
        }
        self.invariantsubtrees = self.dirmap.keys()
        policy.DestdirPolicy.__init__(self, *args, **keywords)

    def test(self):
        if self.macros['lib'] == 'lib':
            # no need to do anything
            return False
        for d in self.invariantsubtrees:
            self.dirmap[d %self.macros] = self.dirmap[d] %self.macros
        return True

    def doFile(self, path):
        destdir = self.macros.destdir
        fullpath = util.joinPaths(destdir, path)
        mode = os.lstat(fullpath)[stat.ST_MODE]
        m = self.recipe.magic[path]
        if stat.S_ISREG(mode) and (
            not m or (m.name != "ELF" and m.name != "ar")):
            self.warn("non-object file with library name %s", path)
            return
        basename = os.path.basename(path)
        currentsubtree = self.currentsubtree % self.macros
        targetdir = self.dirmap[currentsubtree]
        # we want to append whatever path came after the currentsubtree -
        # e.g. if the original path is /usr/lib/subdir/libfoo.a,
        # we still need to add the /subdir/
        targetdir += os.path.dirname(path[len(currentsubtree):])
        target = util.joinPaths(targetdir, basename)
        fulltarget = util.joinPaths(destdir, target)
        if os.path.exists(fulltarget):
            tmode = os.lstat(fulltarget)[stat.ST_MODE]
            tm = self.recipe.magic[target]
            if (not stat.S_ISREG(mode) or not stat.S_ISREG(tmode)):
                # one or both might be symlinks, in which case we do
                # not want to touch this
                return
            if ('abi' in m.contents and 'abi' in tm.contents
                and m.contents['abi'] != tm.contents['abi']):
                # path and target both exist and are of different abis.
                # This means that this is actually a multilib package
                # that properly contains both lib and lib64 items,
                # and we shouldn't try to fix them.
                return
            raise policy.PolicyError(
                "Conflicting library files %s and %s installed" %(
                    path, target))
        self.warn('file %s found in wrong directory, attempting to fix...',
                  path)
        util.mkdirChain(destdir + targetdir)
        if stat.S_ISREG(mode):
            util.rename(destdir + path, fulltarget)
            try:
                self.recipe.recordMove(destdir + path, fulltarget)
            except AttributeError:
                pass
        else:
            # we should have a symlink that may need the contents changed
            contents = os.readlink(fullpath)
            if contents.find('/') == -1:
                # simply rename
                util.rename(destdir + path, destdir + target)
                try:
                    self.recipe.recordMove(destdir + path, fulltarget)
                except AttributeError:
                    pass
            else:
                # need to change the contents of the symlink to point to
                # the new location of the real file
                contentdir = os.path.dirname(contents)
                contenttarget = os.path.basename(contents)
                olddir = os.path.dirname(path)
                if contentdir.startswith('/'):
                    # absolute path
                    if contentdir == olddir:
                        # no need for a path at all, change to local relative
                        os.symlink(contenttarget, destdir + target)
                        os.remove(fullpath)
                        return
                if not contentdir.startswith('.'):
                    raise policy.PolicyError(
                        'Multilib: cannot fix relative path %s in %s -> %s\n'
                        'Library files should be in %s'
                        %(contentdir, path, contents, targetdir))
                # now deal with ..
                # first, check for relative path that resolves to same dir
                i = contentdir.find(olddir)
                if i != -1:
                    dotlist = contentdir[:i].split('/')
                    dirlist = contentdir[i+1:].split('/')
                    if len(dotlist) == len(dirlist):
                        # no need for a path at all, change to local relative
                        os.symlink(contenttarget, destdir + target)
                        os.remove(fullpath)
                        return
                raise policy.PolicyError(
                        'Multilib: cannot fix relative path %s in %s -> %s\n'
                        'Library files should be in %s'
                        %(contentdir, path, contents, targetdir))


class ExecutableLibraries(policy.DestdirPolicy):
    """
    NAME
    ====

    B{C{r.ExecutableLibraries()}} - Set executable bits on library files

    SYNOPSIS
    ========

    C{r.ExecutableLibraries([I{filterexp}] I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The C{r.ExecutableLibraries()} policy changes the mode on library files,
    and warn that it has done so to prevent issues with C{ldconfig}, which
    expects library files to have their executable bits set.

    Note: Do not invoke C{r.ExecutableLibraries()} directly from recipes.
    Invoke C{r.SharedLibrary(subtrees='/path/to/libraries/')} instead.
    """
    requires = (
        ('SharedLibrary', policy.REQUIRED),
    )
    processUnmodified = False
    invariantsubtrees = librarydirs
    invariantinclusions = [
        (r'..*\.so\..*', None, stat.S_IFDIR),
    ]
    recursive = False

    def doFile(self, path):
        fullpath = util.joinPaths(self.macros['destdir'], path)
        if not util.isregular(fullpath):
            return
        mode = os.lstat(fullpath)[stat.ST_MODE]
        if mode & 0111:
            # has some executable bit set
            return
        self.warn('non-executable library %s, changing to mode 0755', path)
        os.chmod(fullpath, 0755)


class CheckSonames(policy.EnforcementPolicy):
    """
    NAME
    ====

    B{C{r.CheckSonames()}} - Warns about shared library packaging errors

    SYNOPSIS
    ========

    C{r.CheckSonames([I{filterexp}] I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The C{r.CheckSonames()} policy warns about various possible shared
    library packaging errors.

    Use C{r.CheckSonames(exceptions=I{filterexp})} for things like directories
    full of plugins.

    EXAMPLES
    ========

    C{r.CheckSonames(exceptions='%(libdir)s/libkdeinit_.*')}

    All the C{libkdeinit_*} files are plugins and do not follow standard
    shared library conventions; this is not an error.
    """
    requires = (
        ('SharedLibrary', policy.REQUIRED),
    )
    processUnmodified = False
    invariantsubtrees = librarydirs
    invariantinclusions = [
	(r'..*\.so', None, stat.S_IFDIR),
    ]
    recursive = False
    nonSymlinkWarn = set()

    def doFile(self, path):
	d = self.macros.destdir
	destlen = len(d)
	l = util.joinPaths(d, path)
	if not os.path.islink(l):
	    m = self.recipe.magic[path]
	    if m and m.name == 'ELF' and 'soname' in m.contents:
		if os.path.basename(path) == m.contents['soname']:
		    target = m.contents['soname']+'.something'
		else:
		    target = m.contents['soname']
                self.warn(
                    '%s is not a symlink but probably should be a link to %s',
                    path, target)
	    return

	# store initial contents
	sopath = util.joinPaths(os.path.dirname(l), os.readlink(l))
	so = util.normpath(sopath)
	# find final file
	while os.path.islink(l):
	    l = util.normpath(util.joinPaths(os.path.dirname(l),
					     os.readlink(l)))

	p = util.joinPaths(d, path)
	linkpath = l[destlen:]
	m = self.recipe.magic[linkpath]

	if m and m.name == 'ELF' and 'soname' in m.contents:
	    if so == linkpath:
                self.info('%s is final path, soname is %s;'
                    ' soname usually is symlink to specific implementation',
                    linkpath, m.contents['soname'])
	    soname = util.normpath(util.joinPaths(
			os.path.dirname(sopath), m.contents['soname']))
	    s = soname[destlen:]
	    try:
		os.stat(soname)
		if not os.path.islink(soname) and s not in self.nonSymlinkWarn:
                    self.nonSymlinkWarn.add(s)
                    self.info('%s has soname %s; best practice is that the'
                              ' filename that matches the soname is a symlink:'
                              ' soname -> soname.minorversion',
                              s, m.contents['soname'])
            except OSError:
                # the missing file case will be fixed up by other policy
                pass


class NormalizeLibrarySymlinks(policy.DestdirPolicy):
    """
    NAME
    ====

    B{C{r.NormalizeLibrarySymlinks()}} - Executes ldconfig in each system
    library directory

    DESCRIPTION
    ===========

    The C{r.NormalizeLibrarySymlinks()} policy runs the C{ldconfig} program
    in each system library directory.

    Without use of this policy class, unowned symlinks may be created when
    C{ldconfig} is run from the shlib tag handler which may then be packaged,
    and cause problems with updating due to newly-packaged files already
    existing on the filesystem.

    Note: Do not invoke C{r.NormalizeLibrarySymlinks()} directly from recipes.
    Invoke C{r.SharedLibrary(subtrees='/path/to/libraries/')} instead.
    """
    requires = (
        ('SharedLibrary', policy.REQUIRED),
        ('ExecutableLibraries', policy.CONDITIONAL_PRIOR),
        ('FixupMultilibPaths', policy.CONDITIONAL_PRIOR),
        ('Strip', policy.CONDITIONAL_SUBSEQUENT),
    )
    processUnmodified = True
    invariantsubtrees = librarydirs

    def do(self):
        macros = self.macros
        subtrees = self.invariantsubtrees
        if self.subtrees:
            subtrees.extend(self.subtrees)
        for path in subtrees:
            path = util.normpath(path % macros)
            fullpath = '/'.join((self.macros.destdir, path))
            if not os.path.exists(fullpath):
                continue
            # this state can only be reached if SharedLibrary is called with
            # bad arguments... see CNP-45
            mode = os.stat(fullpath)[stat.ST_MODE]
            if not stat.S_ISDIR(mode):
                self.error('The subtrees= argument takes directories only;'
                           ' %s is not a directory', path)
                continue
            oldfiles = set(os.listdir(fullpath))
            bootStrapLdConfig = True
            ldConfigPath = '%(destdir)s%(essentialsbindir)s/ldconfig'%macros
            if not (os.path.exists(ldConfigPath)):
                bootStrapLdConfig = False
                ldConfigPath = '%(essentialsbindir)s/ldconfig'%macros
            util.execute('%s -n '%(ldConfigPath + fullpath))

            if not bootStrapLdConfig:
                db = database.Database(self.recipe.cfg.root,
                                       self.recipe.cfg.dbPath)
                ldConfigTroveName = [ x.getName() for x in
                                      db.iterTrovesByPath(ldConfigPath) ]
                if ldConfigTroveName:
                    ldConfigTroveName = ldConfigTroveName[0]
                else:
                    ldConfigTroveName = 'glibc:runtime'

                try:
                    if ldConfigTroveName in self.recipe._getTransitiveBuildRequiresNames():
                        self.recipe.reportExcessBuildRequires(ldConfigTroveName)
                    else:
                        self.recipe.reportMissingBuildRequires(ldConfigTroveName)
                except AttributeError:
                    # older Conary that does not have
                    # reportExcessBuildRequires or even the older
                    # reportMissingBuildRequires or
                    # _getTransitiveBuildRequiresNames
                    pass

            newfiles = set(os.listdir(fullpath))
            addedfiles = newfiles - oldfiles
            removedfiles = oldfiles - newfiles
            if addedfiles:
                self.info('ldconfig added the following new files in %s: %s',
                          path, ', '.join(sorted(list(addedfiles))))
            if removedfiles:
                self.warn('ldconfig removed files in %s: %s', path,
                          ', '.join(sorted(list(removedfiles))))
