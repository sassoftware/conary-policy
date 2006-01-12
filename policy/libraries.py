#
# Copyright (c) 2004-2006 rPath, Inc.
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

import os
import stat

from conary.lib import util
from conary.build import policy


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


class SharedLibrary(policy.PackagePolicy):
    """
    Mark system shared libaries as such so that ldconfig will be run:
    C{r.SharedLibrary(subtrees=I{path})} to mark a path as containing
    shared libraries; C{r.SharedLibrary(I{filterexp})} to mark a file.

    C{r.SharedLibrary} does B{not} walk entire directory trees.  Every
    directory that you want to add must be passed in using the
    C{subtrees} keyword.
    """
    requires = (
        ('ExecutableLibraries', policy.REQUIRED),
        ('CheckSonames', policy.REQUIRED),
        ('NormalizeLibrarySymlinks', policy.REQUIRED),
        ('Provides', policy.REQUIRED),
        ('Requires', policy.REQUIRED),
    )

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
                self.dbg(filename)
		self.recipe.autopkg.pathMap[filename].tags.set("shlib")


class FixupMultilibPaths(policy.DestdirPolicy):
    """
    Fix up (and warn) when programs do not know about C{%(lib)s} and they
    are supposed to be installing to C{lib64} but install to C{lib} instead.
    """
    requires = (
        ('Strip', policy.CONDITIONAL_SUBSEQUENT),
    )
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
        else:
            # we should have a symlink that may need the contents changed
            contents = os.readlink(fullpath)
            if contents.find('/') == -1:
                # simply rename
                util.rename(destdir + path, destdir + target)
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
    The C{ldconfig} program will complain if libraries do not have have
    executable bits set; this policy changes the mode and warns that
    it has done so.

    Do not invoke C{r.ExecutableLibraries()} from recipes; invoke
    C{r.SharedLibrary(subtrees='/path/to/libraries/')} instead.
    """
    requires = (
        ('SharedLibrary', policy.REQUIRED),
    )
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
    Warns about various possible shared library packaging errors:
    C{r.CheckSonames(exceptions=I{filterexp})} for things like directories
    full of plugins.
    """
    requires = (
        ('SharedLibrary', policy.REQUIRED),
    )
    invariantsubtrees = librarydirs
    invariantinclusions = [
	(r'..*\.so', None, stat.S_IFDIR),
    ]
    recursive = False

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
                self.dbg('%s is final path, soname is %s;'
                    ' soname usually is symlink to specific implementation',
                    linkpath, m.contents['soname'])
	    soname = util.normpath(util.joinPaths(
			os.path.dirname(sopath), m.contents['soname']))
	    s = soname[destlen:]
	    try:
		os.stat(soname)
		if not os.path.islink(soname):
                    self.warn('%s has soname %s; therefore should be a symlink',
                              s, m.contents['soname'])
	    except:
                self.warn("%s implies %s, which does not exist --"
                          " use r.Ldconfig('%s')?",
                          path, s, os.path.dirname(path))


class NormalizeLibrarySymlinks(policy.DestdirPolicy):
    """
    Runs the ldconfig program in each system library directory.
    Without this, when ldconfig is run from the shlib tag handler,
    it can create unowned symlinks that are later packaged and
    cause problems updating because a newly-packaged file already
    exists on the filesystem.

    Pass in additional system libraries only by calling
    C{r.SharedLibrary(subtrees='I{/path/to/libraries/}')}; do not
    pass them in directly.  Exceptions can be passed in directly by
    calling C{r.NormalizeLibrarySymlinks(exceptions='I{/path/to/libraries/}')}.
    """
    requires = (
        ('SharedLibrary', policy.REQUIRED),
    )
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
            oldfiles = set(os.listdir(fullpath))
            util.execute('%(essentialsbindir)s/ldconfig -n '%macros + fullpath)
            newfiles = set(os.listdir(fullpath))
            addedfiles = newfiles - oldfiles
            removedfiles = oldfiles - newfiles
            if addedfiles:
                self.warn('ldconfig found missing files in %s: %s', path,
                          ', '.join(sorted(list(addedfiles))))
            if removedfiles:
                self.warn('ldconfig removed files in %s: %s', path,
                          ', '.join(sorted(list(removedfiles))))
