#
# Copyright (c) 2004-2007 rPath, Inc.
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
import tempfile
import filecmp
import shutil
import zipfile

from conary.lib import magic, util
from conary.build import policy
from conary.local import database


def _findProgPath(prog, db, recipe):
    # ignore arguments
    prog = prog.split(' ')[0]
    if prog.startswith('/'):
        progPath = prog
    else:
        macros = recipe.macros
        searchPath = [macros.essentialbindir,
                      macros.bindir,
                      macros.essentialsbindir,
                      macros.sbindir]
        searchPath.extend([x for x in ['/bin', '/usr/bin', '/sbin', '/usr/sbin']
                           if x not in searchPath])
        searchPath.extend([x for x in os.getenv('PATH', '').split(os.path.pathsep)
                           if x not in searchPath])
        progPath = util.findFile(prog, searchPath)

    progTroveName =  [ x.getName() for x in db.iterTrovesByPath(progPath) ]
    if progTroveName:
        progTroveName = progTroveName[0]
        try:
            if progTroveName in recipe._getTransitiveBuildRequiresNames():
                recipe.reportExcessBuildRequires(progTroveName)
            else:
                recipe.reportMisingBuildRequires(progTroveName)
        except AttributeError:
            # older conary
            pass

    return progPath


class NormalizeCompression(policy.DestdirPolicy):
    """
    NAME
    ====

    B{C{r.NormalizeCompression()}} - Compress files with maximum compression

    SYNOPSIS
    ========

    C{r.NormalizeCompression([I{filterexp}] I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The C{r.NormalizeCompression()} policy compresses files with maximum
    compression, and without data which may change from invocation, to
    invocation.

    Recompresses .gz files with -9 -n, and .bz2 files with -9, to get maximum
    compression and avoid meaningless changes overpopulating the database.
    Ignores man/info pages, as they are encountered separately while making other
    changes to man/info pages later.

    EXAMPLES
    ========

    C{r.NormalizeCompression(exceptions='%(thistestdir)s/.*')}

    This package has test files that are tested byte-for-byte and
    cannot be modified at all and still pass the tests.
    """
    processUnmodified = False
    invariantexceptions = [
        '%(mandir)s/man.*/',
        '%(infodir)s/',
    ]
    invariantinclusions = [
        ('.*\.(gz|bz2)', None, stat.S_IFDIR),
    ]
    db = None
    gzip = None
    bzip = None

    def doFile(self, path):
        m = self.recipe.magic[path]
        if not m:
            return

        # Note: uses external gzip/bunzip if they exist because a
        # pipeline is faster in a multiprocessing environment

        def _mktmp(fullpath):
            fd, path = tempfile.mkstemp('.temp', '', os.path.dirname(fullpath))
            os.close(fd)
            return path

        def _move(tmppath, fullpath):
            os.chmod(tmppath, os.lstat(fullpath).st_mode)
            os.rename(tmppath, fullpath)

        def _findProg(prog):
            if not self.db:
                self.db = database.Database(self.recipe.cfg.root,
                                       self.recipe.cfg.dbPath)
            return _findProgPath(prog, self.db, self.recipe)

        fullpath = self.macros.destdir+path
        if m.name == 'gzip' and \
           (m.contents['compression'] != '9' or 'name' in m.contents):
            tmppath = _mktmp(fullpath)
            if not self.gzip:
                self.gzip = _findProg('gzip')
            util.execute('%s -dc %s | %s -f -n -9 > %s'
                         %(self.gzip, fullpath, self.gzip, tmppath))
            _move(tmppath, fullpath)
            del self.recipe.magic[path]
        if m.name == 'bzip' and m.contents['compression'] != '9':
            tmppath = _mktmp(fullpath)
            if not self.bzip:
                self.bzip = _findProg('bzip2')
            util.execute('%s -dc %s | %s -9 > %s'
                         %(self.bzip, fullpath, self.bzip, tmppath))
            _move(tmppath, fullpath)
            del self.recipe.magic[path]


class NormalizeManPages(policy.DestdirPolicy):
    """
    NAME
    ====

    B{C{r.NormalizeManPages()}} - Make all man pages follow sane system policy

    SYNOPSIS
    ========

    C{r.NormalizeManPages([I{filterexp}] I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The C{r.NormalizeManPages()} policy makes all system manual pages
    follow sane system policy

    Note: This policy class is not called directly from recipes, and does not
    honor exceptions.

    Some of the following tasks are performed against system manual pages via
    C{r.NormalizeManPages}:

    - Fix all man pages' contents:
    - remove instances of C{/?%(destdir)s} from all man pages
    - C{.so foo.n} becomes a symlink to foo.n
    - (re)compress all man pages with gzip -f -n -9
    - change all symlinks to point to .gz (if they don't already)
    - make all man pages be mode 644
    """
    requires = (
        ('ReadableDocs', policy.CONDITIONAL_SUBSEQUENT),
    )

    def _findProg(self, prog):
        if not self.db:
            self.db = database.Database(self.recipe.cfg.root,
                                        self.recipe.cfg.dbPath)
        return _findProgPath(prog, self.db, self.recipe)

    # Note: not safe for derived packages; needs to check in each
    # internal function for unmodified files
    def _uncompress(self, dirname, names):
        for name in names:
            path = dirname + os.sep + name
            if name.endswith('.gz') and util.isregular(path):
                if not self.gunzip:
                    self.gunzip = self._findProg('gunzip')
                util.execute('gunzip ' + dirname + os.sep + name)
                try:
                    self.recipe.recordMove(util.joinPaths(dirname, name),
                            util.joinPaths(dirname, name)[:-3])
                except AttributeError:
                    pass
            if name.endswith('.bz2') and util.isregular(path):
                if not self.bunzip:
                    self.bunzip = self._findProg('bunzip2')
                util.execute('bunzip2 ' + dirname + os.sep + name)
                try:
                    self.recipe.recordMove(util.joinPaths(dirname, name),
                            util.joinPaths(dirname, name)[:-4])
                except AttributeError:
                    pass

    def _touchup(self, dirname, names):
        """
        remove destdir, fix up modes, ensure that it is legal UTF-8
        """
        mode = os.lstat(dirname)[stat.ST_MODE]
        if mode & 0777 != 0755:
            os.chmod(dirname, 0755)
        for name in names:
            path = dirname + os.sep + name
            mode = os.lstat(path)[stat.ST_MODE]
            # avoid things like symlinks
            if not stat.S_ISREG(mode):
                continue
            if mode & 0777 != 0644:
                os.chmod(path, 0644)
            f = file(path, 'r+')
            data = f.read()
            write = False
            try:
                data.decode('utf-8')
            except:
                try:
                    data = data.decode('iso-8859-1').encode('utf-8')
                    write = True
                except:
                    self.error('unable to decode %s as utf-8 or iso-8859-1',
                               path)
            if data.find(self.destdir) != -1:
                write = True
                # I think this is cheaper than using a regexp
                data = data.replace('/'+self.destdir, '')
                data = data.replace(self.destdir, '')

            if write:
                f.seek(0)
                f.truncate(0)
                f.write(data)


    def _sosymlink(self, dirname, names):
        section = os.path.basename(dirname)
        for name in names:
            path = dirname + os.sep + name
            if util.isregular(path):
                # if only .so, change to symlink
                f = file(path)
                lines = f.readlines(512) # we really don't need the whole file
                f.close()

                # delete comment lines first
                newlines = []
                for line in lines:
                    # newline means len(line) will be at least 1
                    if len(line) > 1 and not self.commentexp.search(line[:-1]):
                        newlines.append(line)
                lines = newlines

                # now see if we have only a .so line to replace
                # only replace .so with symlink if the file exists
                # in order to deal with searchpaths
                if len(lines) == 1:
                    line = lines[0]
                    # remove newline and other trailing whitespace if it exists
                    line = line.rstrip()
                    match = self.soexp.search(line)
                    if match:
                        matchlist = match.group(1).split('/')
                        l = len(matchlist)
                        if l == 1 or matchlist[l-2] == section:
                            # no directory specified, or in the same
                            # directory:
                            targetpath = os.sep.join((dirname, matchlist[l-1]))
                            if (os.path.exists(targetpath) and
                                os.path.isfile(targetpath)):
                                self.info('replacing %s (%s) with symlink %s',
                                          name, match.group(0),
                                          os.path.basename(match.group(1)))
                                os.remove(path)
                                os.symlink(os.path.basename(match.group(1)),
                                           path)
                        else:
                            # either the canonical .so manN/foo.N or an
                            # absolute path /usr/share/man/manN/foo.N
                            # .so is relative to %(mandir)s and the other
                            # man page is in a different dir, so add ../
                            target = "../%s/%s" %(matchlist[l-2],
                                                  matchlist[l-1])
                            targetpath = os.sep.join((dirname, target))
                            if os.path.exists(targetpath):
                                self.info('replacing %s (%s) with symlink %s',
                                          name, match.group(0), target)
                                os.remove(path)
                                os.symlink(target, path)

    def _compress(self, dirname, names):
        for name in names:
            path = dirname + os.sep + name
            if util.isregular(path):
                if not self.gzip:
                    self.gzip = self._findProg('gzip')
                util.execute('gzip -f -n -9 ' + dirname + os.sep + name)
                try:
                    self.recipe.recordMove(dirname + os.sep + name,
                            dirname + os.sep + name + '.gz')
                except AttributeError:
                    pass

    def _gzsymlink(self, dirname, names):
        for name in names:
            path = dirname + os.sep + name
            if os.path.islink(path):
                # change symlinks to .gz -> .gz
                contents = os.readlink(path)
                os.remove(path)
                if not contents.endswith('.gz'):
                    contents = contents + '.gz'
                if not path.endswith('.gz'):
                    path = path + '.gz'
                os.symlink(util.normpath(contents), path)

    def __init__(self, *args, **keywords):
        policy.DestdirPolicy.__init__(self, *args, **keywords)
        self.soexp = re.compile(r'^\.so (.*\...*)$')
        self.commentexp = re.compile(r'^\.\\"')
        self.db = None
        self.gzip = None
        self.gunzip = None
        self.bunzip = None

    def do(self):
        for manpath in sorted(list(set((
                self.macros.mandir,
                os.sep.join((self.macros.x11prefix, 'man')),
                os.sep.join((self.macros.krbprefix, 'man')),)))
            ):
            manpath = self.macros.destdir + manpath
            self.destdir = self.macros['destdir'][1:] # without leading /
            # uncompress all man pages
            os.path.walk(manpath, NormalizeManPages._uncompress, self)
            # remove '/?%(destdir)s' and fix modes
            os.path.walk(manpath, NormalizeManPages._touchup, self)
            # .so foo.n becomes a symlink to foo.n
            os.path.walk(manpath, NormalizeManPages._sosymlink, self)
            # recompress all man pages
            os.path.walk(manpath, NormalizeManPages._compress, self)
            # change all symlinks to point to .gz (if they don't already)
            os.path.walk(manpath, NormalizeManPages._gzsymlink, self)


class NormalizeInfoPages(policy.DestdirPolicy):
    """
    NAME
    ====

    B{C{r.NormalizeInfoPages()}} - Compress files with maximum compression

    SYNOPSIS
    ========

    C{r.NormalizeInfoPages([I{filterexp}] I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The C{r.NormalizeInfoPages()} policy properly compresses info files,
    and removes the info directory file.

    EXAMPLES
    ========

    The only recipe invocation possible for C{r.NormalizeInfoPages} is
    C{r.NormalizeInfoPages(exceptions='%(infodir)s/dir')} in the recipe that
    should own the info directory file (normally texinfo).
    """
    requires = (
        ('ReadableDocs', policy.CONDITIONAL_SUBSEQUENT),
    )
    # Not safe for derived packages in this form, needs explicit checks
    def do(self):
        dir = self.macros['infodir']+'/dir'
        fsdir = self.macros['destdir']+dir
        if os.path.exists(fsdir):
            if not self.policyException(dir):
                util.remove(fsdir)
        if os.path.isdir('%(destdir)s/%(infodir)s' %self.macros):
            infofilespath = '%(destdir)s/%(infodir)s' %self.macros
            infofiles = os.listdir(infofilespath)
            for file in infofiles:
                self._moveToInfoRoot(file)
            infofiles = os.listdir(infofilespath)
            for file in infofiles:
                self._processInfoFile(file)

    def __init__(self, *args, **keywords):
        policy.DestdirPolicy.__init__(self, *args, **keywords)
        self.db = None
        self.gzip = None
        self.gunzip = None
        self.bunzip = None

    def _findProg(self, prog):
        if not self.db:
            self.db = database.Database(self.recipe.cfg.root,
                                        self.recipe.cfg.dbPath)
        return _findProgPath(prog, self.db, self.recipe)

    def _moveToInfoRoot(self, file):
        infofilespath = '%(destdir)s/%(infodir)s' %self.macros
        fullfile = '/'.join((infofilespath, file))
        if os.path.isdir(fullfile):
            for subfile in os.listdir(fullfile):
                self._moveToInfoRoot('/'.join((file, subfile)))
            shutil.rmtree(fullfile)
        elif os.path.dirname(fullfile) != infofilespath:
            shutil.move(fullfile, infofilespath)
            try:
                self.recipe.recordMove(fullfile,
                        util.joinPaths(infofilespath,
                            os.path.basename(fullfile)))
            except AttributeError:
                pass

    def _processInfoFile(self, file):
        syspath = '%(destdir)s/%(infodir)s/' %self.macros + file
        path = '%(infodir)s/' %self.macros + file
        if not self.policyException(path):
            m = self.recipe.magic[path]
            if not m or m.name not in ('gzip', 'bzip'):
                # not compressed
                if not self.gzip:
                    self.gzip = self._findProg('gzip')
                util.execute('gzip -f -n -9 %s' %syspath)
                try:
                    self.recipe.recordMove(syspath, syspath + '.gz')
                except AttributeError:
                    pass
                del self.recipe.magic[path]
            elif m.name == 'gzip' and \
                (m.contents['compression'] != '9' or \
                'name' in m.contents):
                if not self.gzip:
                    self.gzip = self._findProg('gzip')
                if not self.gunzip:
                    self.gunzip = self._findProg('gunzip')
                util.execute('gunzip %s; gzip -f -n -9 %s'
                            %(syspath, syspath[:-3]))
                # filename didn't change, so don't record it in the manifest
                del self.recipe.magic[path]
            elif m.name == 'bzip':
                # should use gzip instead
                if not self.gzip:
                    self.gzip = self._findProg('gzip')
                if not self.bunzip:
                    self.bunzip = self._findProg('bunzip2')
                util.execute('bunzip2 %s; gzip -f -n -9 %s'
                            %(syspath, syspath[:-4]))
                try:
                    self.recipe.recordMove(syspath, syspath[:-4] + '.gz')
                except AttributeError:
                    pass
                del self.recipe.magic[path]


class NormalizeInitscriptLocation(policy.DestdirPolicy):
    """
    NAME
    ====

    B{C{r.NormalizeInitscriptLocation()}} - Properly locates init scripts

    SYNOPSIS
    ========

    C{r.NormalizeInitscriptLocation([I{filterexp}] I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The C{r.NormalizeInitscriptLocation()} policy puts init scripts in their
    proper location, resolving ambiguity about their proper location.

    Moves all init scripts from /etc/rc.d/init.d/ to their official location.
    """

    requires = (
        ('RelativeSymlinks', policy.CONDITIONAL_SUBSEQUENT),
        ('NormalizeInterpreterPaths', policy.CONDITIONAL_SUBSEQUENT),
    )
    processUnmodified = False
    # need both of the next two lines to avoid following /etc/rc.d/init.d
    # if it is a symlink
    invariantsubtrees = [ '/etc/rc.d' ]
    invariantinclusions = [ '/etc/rc.d/init.d/' ]

    def test(self):
        return self.macros['initdir'] != '/etc/rc.d/init.d'

    def doFile(self, path):
        basename = os.path.basename(path)
        target = util.joinPaths(self.macros['initdir'], basename)
        if os.path.exists(self.macros['destdir'] + os.sep + target):
            raise policy.PolicyError(
                "Conflicting initscripts %s and %s installed" %(
                    path, target))
        util.mkdirChain(self.macros['destdir'] + os.sep +
                        self.macros['initdir'])
        util.rename(self.macros['destdir'] + path,
                    self.macros['destdir'] + target)
        try:
            self.recipe.recordMove(self.macros['destdir'] + path,
                    self.macros['destdir'] + target)
        except AttributeError:
            pass


class NormalizeInitscriptContents(policy.DestdirPolicy):
    """
    NAME
    ====

    B{C{r.NormalizeInitscriptContents()}} - Fixes common errors within init scripts

    SYNOPSIS
    ========

    C{r.NormalizeInitscriptContents([I{filterexp}] I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The C{r.NormalizeInitscriptContents()} policy fixes common errors within
    init scripts, and adds some dependencies if needed.

    EXAMPLES
    ========

    C{r.NormalizeInitscriptContents(exceptions='%(initdir)s/foo')}

    Use this in the unprecedented case that C{r.NormalizeInitscriptContents}
    damages an init script.
    """
    requires = (
        # for invariantsubtree to be sufficient
        ('NormalizeInitscriptLocation', policy.REQUIRED_PRIOR),
        ('RelativeSymlinks', policy.REQUIRED_PRIOR),
        # for adding requirements
        ('Requires', policy.REQUIRED_SUBSEQUENT),
    )
    processUnmodified = False
    invariantsubtrees = [ '%(initdir)s' ]
    invariantinclusions = [ ('.*', 0400, stat.S_IFDIR), ]

    def doFile(self, path):
        m = self.recipe.macros
        fullpath = '/'.join((m.destdir, path))
        if os.path.islink(fullpath):
            linkpath = os.readlink(fullpath)
            if m.destdir not in linkpath:
                # RelativeSymlinks has already run. linkpath is relative to
                # fullpath
                newpath = util.joinPaths(os.path.dirname(fullpath), linkpath)
                if os.path.exists(newpath):
                    fullpath = newpath
                else:
                    # If the target of an init script is not present, don't
                    # error, DanglingSymlinks will address this situation.
                    self.warn('%s is a symlink to %s, which does not exist.' % \
                            (path, linkpath))
                    return

        contents = file(fullpath).read()
        modified = False
        if '/etc/rc.d/init.d' in contents:
            contents = contents.replace('/etc/rc.d/init.d', m.initdir)
            modified = True

        if '%(initdir)s/functions' %m in contents:
            self.recipe.Requires('initscripts:runtime', util.literalRegex(path))

        if modified:
            file(fullpath, 'w').write(contents)


class NormalizeAppDefaults(policy.DestdirPolicy):
    """
    NAME
    ====

    B{C{r.NormalizeAppDefaults()}} - Locate X application defaults files

    SYNOPSIS
    ========

    C{r.NormalizeAppDefaults([I{filterexp}])}

    DESCRIPTION
    ===========

    The C{r.NormalizeAppDefaults()} policy locates X application defaults
    files.

    No exceptions to this policy are honored.
    """
    # not safe in this form for derived packages
    def do(self):
        e = '%(destdir)s/%(sysconfdir)s/X11/app-defaults' % self.macros
        if not os.path.isdir(e):
            return

        x = '%(destdir)s/%(x11prefix)s/lib/X11/app-defaults' % self.macros
        self.warn('app-default files misplaced in'
                  ' %(sysconfdir)s/X11/app-defaults' % self.macros)
        if os.path.islink(x):
            util.remove(x)
        util.mkdirChain(x)
        for file in os.listdir(e):
            util.rename(util.joinPaths(e, file),
                        util.joinPaths(x, file))
            try:
                self.recipe.recordMove(util.joinPaths(e, file),
                        util.joinPaths(x, file))
            except AttributeError:
                pass


class NormalizeInterpreterPaths(policy.DestdirPolicy):
    """
    NAME
    ====

    B{C{r.NormalizeInterpreterPaths()}} - Rewrites interpreter paths in
    scripts

    SYNOPSIS
    ========

    C{r.NormalizeInterpreterPaths([I{filterexp}] I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The C{r.NormalizeInterpreterPaths()} policy re-writes the paths, in
    particular changing indirect calls through env to direct calls.

    Exceptions to this policy should only be made when they are part of the
    explicit calling convention of a script where the location of the final
    interpreter depend on the user's C{PATH}.

    EXAMPLES
    ========

    C{r.NormalizeInterpreterPaths(exceptions=".*")}

    Do not modify any interpreter paths for this package.  Not
    generally recommended.
    """
    processUnmodified = False
    invariantexceptions = [ '%(thisdocdir.literalRegex)s/', ]

    def doFile(self, path):
        destdir = self.recipe.macros.destdir
        d = util.joinPaths(destdir, path)
        
        mode = os.lstat(d)[stat.ST_MODE]
        if not mode & 0111:
            # we care about interpreter paths only in executable scripts
            return
        m = self.recipe.magic[path]
        if m and m.name == 'script':
           
            if self._correctInterp(m, path):
                del self.recipe.magic[path]
                m = self.recipe.magic[path]
            if self._correctEnv(m, path):
                del self.recipe.magic[path]

    def _correctInterp(self, m, path):
        destdir = self.recipe.macros.destdir
        d = util.joinPaths(destdir, path)

        interp = m.contents['interpreter']
        interpBase = os.path.basename(interp)

        found = False

        if not os.path.exists('/'.join((destdir, interp))) and not os.path.exists(interp):
            #try tro remove 'local' part
            if '/local/' in interp:
                normalized = interp.replace('/local', '')
                if os.path.exists('/'.join((destdir, normalized))) or os.path.exists(normalized):
                    found = True
                if not found:
                    cadidates = (
                                self.recipe.macros.bindir,
                                self.recipe.macros.sbindir,
                                self.recipe.macros.essentialbindir,
                                self.recipe.macros.essentialsbindir,
                                )
                    for i in cadidates:
                        if os.path.exists('/'.join((destdir, i, interpBase))):
                            normalized = util.joinPaths(i, interpBase)
                            found = True
                            break
                    if not found:
                        #try to find in '/bin', '/sbin', '/usr/bin', '/usr/sbin'
                        for i in '/usr/bin', '/bin', '/usr/sbin', '/sbin':
                            normalized = '/'.join((i, interpBase))
                            if os.path.exists(normalized):
                                found = True
                                break
                        if not found:
                            self.warn('The interpreter path %s in %s does not exist!', interp, path)
       
        if found:
                line = m.contents['line']
                normalized = line.replace(interp, normalized)
                self._changeInterpLine(d, '#!' + normalized + '\n')
                self.info('changing %s to %s in %s',
                            line, normalized, path)

        return found
       
    def _correctEnv(self, m, path):
        destdir = self.recipe.macros.destdir
        d = util.joinPaths(destdir, path)

        interp = m.contents['interpreter']
        if interp.find('/bin/env') != -1: #finds /usr/bin/env too...
            line = m.contents['line']
            # rewrite to not have env
            wordlist = [ x for x in line.split() ]
            if len(wordlist) == 1:
                self.error("Interpreter is not given for %s in %s", wordlist[0], path)
                return
            wordlist.pop(0) # get rid of env
            # first look in package
            fullintpath = util.checkPath(wordlist[0], root=destdir)
            if fullintpath == None:
                # then look on installed system
                fullintpath = util.checkPath(wordlist[0])
            if fullintpath == None:
                self.error("Interpreter %s for file %s not found, could not convert from /usr/bin/env syntax", wordlist[0], path)
                return False

            wordlist[0] = fullintpath

            self._changeInterpLine(d, '#!'+" ".join(wordlist)+'\n')
            self.info('changing %s to %s in %s',
                        line, " ".join(wordlist), path)
            return True
        return False

    def _changeInterpLine(self, path, newline):
        mode = os.lstat(path)[stat.ST_MODE]
        # we need to be able to write the file
        os.chmod(path, mode | 0600)
        f = file(path, 'r+')
        l = f.readlines()
        l[0] = newline
        f.seek(0)
        f.truncate(0)# we may have shrunk the file, avoid garbage
        f.writelines(l)
        f.close()
        # revert any change to mode
        os.chmod(path, mode)
       

class NormalizePamConfig(policy.DestdirPolicy):
    """
    NAME
    ====

    B{C{r.NormalizePamConfig()}} - Adjust PAM configuration files

    SYNOPSIS
    ========

    C{r.NormalizePamConfig([I{filterexp}] I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The C{r.NormalizePamConfig()} policy adjusts PAM configuration files, and
    remove references to older module paths such as: C{/lib/security/$ISA} as
    there is no need for such paths in modern PAM libraries.

    Exceptions to this policy should never be required.
    """
    processUnmodified = False
    invariantsubtrees = [
        '%(sysconfdir)s/pam.d/',
    ]

    def doFile(self, path):
        d = util.joinPaths(self.recipe.macros.destdir, path)
        mode = os.lstat(d)[stat.ST_MODE]
        if stat.S_ISLNK(mode):
            # we'll process whatever this is pointing to whenever we
            # get there.
            return
        if not (mode & 0200):
            os.chmod(d, mode | 0200)
        f = file(d, 'r+')
        l = f.readlines()
        l = [x.replace('/lib/security/$ISA/', '') for x in l]
        stackRe = re.compile('(.*)required.*pam_stack.so.*service=(.*)')
        def removeStack(line):
            m = stackRe.match(line)
            if m:
                return '%s include %s\n'%(m.group(1), m.group(2))
            return line
        l = [removeStack(x) for x in l]
        f.seek(0)
        f.truncate(0) # we may have shrunk the file, avoid garbage
        f.writelines(l)
        f.close()
        os.chmod(d, mode)

class NormalizePythonInterpreterVersion(policy.DestdirPolicy):
    """
    NAME
    ====

    B{C{r.NormalizePythonInterpreterVersion()}} - Provides version-specific path to python interpreter in python program files

    SYNOPSIS
    ========

    C{r.NormalizePythonInterpreterVersion([I{filterexp}], I{exceptions=filterexp}, I{versionMap=((from, to), ...)}])}

    DESCRIPTION
    ===========

    The C{r.NormalizePythonInterpreterVersion()} policy ensures that
    python script files have a version-specific path to the
    interpreter if possible.

    KEYWORDS
    ========

    B{versionMap} : Specify mappings of interpreter version changes
    to make for python scripts.

    EXAMPLES
    ========

    C{r.NormalizePythonInterpreterVersion(versionMap=(
        ('%(bindir)s/python', '%(bindir)s/python2.5'),
        ('%(bindir)s/python25', '%(bindir)s/python2.5')
    ))}

    Specify that any scripts with an interpreter of C{/usr/bin/python}
    or C{/usr/bin/python25} should be changed to C{/usr/bin/python2.5}.
    """

    requires = (
        ('NormalizeInterpreterPaths', policy.CONDITIONAL_PRIOR),
    )

    keywords = {'versionMap': {}}

    processUnmodified = False

    def updateArgs(self, *args, **keywords):
        if 'versionMap' in keywords:
            versionMap = keywords.pop('versionMap')
            if type(versionMap) in (list, tuple):
                versionMap = dict(versionMap)
            self.versionMap.update(versionMap)
        policy.DestdirPolicy.updateArgs(self, *args, **keywords)

    def preProcess(self):
        self.interpreterRe = re.compile(".*python[-0-9.]+")
        self.interpMap = {}
        versionMap = {}
        for item in self.versionMap.items():
            versionMap[item[0]%self.macros] = item[1]%self.macros
        self.versionMap = versionMap

    def doFile(self, path):
        destdir = self.recipe.macros.destdir
        d = util.joinPaths(destdir, path)
        mode = os.lstat(d)[stat.ST_MODE]
        m = self.recipe.magic[path]
        if m and m.name == 'script':
            interp = m.contents['interpreter']
            if '/python' not in interp:
                # we handle only python scripts here
                return
            if interp in self.versionMap.keys():
                normalized = self.versionMap[interp]
            elif not self._isNormalizedInterpreter(interp):
                # normalization
                if self.interpMap.has_key(interp):
                    normalized = self.interpMap[interp]
                else:
                    normalized = self._normalize(interp)
                    if normalized:
                        self.interpMap[interp] = normalized
                    else:
                        self.warn('No version-specific python interpreter '
                                  'found for %s in %s', interp, path)
                        return
            else:
                return

            # we need to be able to write the file
            os.chmod(d, mode | 0600)
            f = file(d, 'r+')
            l = f.readlines()
            l[0] = l[0].replace(interp, normalized)
            # we may have shrunk the file, avoid garbage
            f.seek(0)
            f.truncate(0)
            f.writelines(l)
            f.close()
            # revert any change to mode
            os.chmod(d, mode)

            self.info('changed %s to %s in %s', interp, normalized, path)
            del self.recipe.magic[path]

    def _isNormalizedInterpreter(self, interp):
        return os.path.basename(interp).startswith('python') and self.interpreterRe.match(interp)

    def _normalize(self, interp):
        dir = self.recipe.macros.destdir
       
        interpFull = '/'.join((dir, interp))
        interpFullBase = os.path.basename(interpFull)
        interpFullDir = os.path.dirname(interpFull)
        interpDir = os.path.dirname(interp)

        links = []
        if os.path.exists(interpFull):
            for i in os.listdir(interpFullDir):
                if os.path.samefile(interpFull, '/'.join((interpFullDir, i))):
                    links += [i]
            path = sorted(links, key=len, reverse=True)
            if path and self._isNormalizedInterpreter('/'.join((interpFullDir, path[0]))):
                return os.path.join(interpDir, path[0])
       
            links = []
            for i in os.listdir(interpFullDir):
                try:
                    if filecmp.cmp(interpFull, '/'.join((interpFullDir, i))):
                        links += [i]
                except IOError:
                    # this is a fallback for a bad install anyway, so
                    # a failure here is both unusual and not important
                    pass
            path = sorted(links, key=len, reverse=True)
            if path and self._isNormalizedInterpreter('/'.join((interpFullDir, path[0]))):
                return os.path.join(interpDir, path[0])
        
        else:
            db = database.Database('/', self.recipe.cfg.dbPath)
            pythonTroveList = db.iterTrovesByPath(interp)
            for trove in pythonTroveList:
                pathList = [x[1] for x in trove.iterFileList()]
                links += [x for x in pathList if x.startswith(interp)]
            path = sorted(links, key=len, reverse=True)
            if path and self._isNormalizedInterpreter(path[0]):
                return path[0]

        return None

class NormalizePythonEggs(policy.DestdirPolicy):
    invariantinclusions = [
        ('.*/python[^/]*/site-packages/.*\.egg', stat.S_IFREG),
    ]

    requires = (
        ('RemoveNonPackageFiles', policy.CONDITIONAL_PRIOR),
    )

    def doFile(self, path):
        dir = self.recipe.macros.destdir
        fullPath = util.joinPaths(dir, path)
        m = magic.magic(fullPath)
        if not (m and m.name == 'ZIP'):
            # if it's not a zip, we can't unpack it, PythonEggs will raise
            # an error on this path
            return
        tmpPath = tempfile.mkdtemp(dir = self.recipe.macros.builddir)
        util.execute("unzip -q -o -d '%s' '%s'" % (tmpPath, fullPath))
        self._addActionPathBuildRequires(['unzip'])
        os.unlink(fullPath)
        shutil.move(tmpPath, fullPath)


# Note: NormalizeLibrarySymlinks is in libraries.py
