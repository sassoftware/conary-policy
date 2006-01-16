#
# Copyright (c) 2004-2005 rPath, Inc.
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
import re
import stat
import tempfile

from conary.lib import util
from conary.build import policy


class NormalizeCompression(policy.DestdirPolicy):
    """
    Compresses files with maximum compression and without data that can
    change from invocation to invocation;
    C{r.NormalizeCompression(exceptions=I{filterexp}} to disable this
    policy for a file.

    Recompresses .gz files with -9 -n, and .bz2 files with -9, to get maximum
    compression and avoid meaningless changes overpopulating the database.
    Ignores man/info pages, as we get them separately while making other
    changes to man/info pages later.
    """
    invariantexceptions = [
        '%(mandir)s/man.*/',
        '%(infodir)s/',
    ]
    invariantinclusions = [
        ('.*\.(gz|bz2)', None, stat.S_IFDIR),
    ]
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

        fullpath = self.macros.destdir+path
        if m.name == 'gzip' and \
           (m.contents['compression'] != '9' or 'name' in m.contents):
            tmppath = _mktmp(fullpath)
            util.execute('/bin/gzip -dc %s | /bin/gzip -f -n -9 > %s'
                         %(fullpath, tmppath))
            _move(tmppath, fullpath)
            del self.recipe.magic[path]
        if m.name == 'bzip' and m.contents['compression'] != '9':
            tmppath = _mktmp(fullpath)
            util.execute('/usr/bin/bzip2 -dc %s | /usr/bin/bzip2 -9 > %s'
                         %(fullpath, tmppath))
            _move(tmppath, fullpath)
            del self.recipe.magic[path]


class NormalizeManPages(policy.DestdirPolicy):
    """
    Make all man pages follow sane system policy; not called from recipes,
    as there are no exceptions, period.
     - Fix all man pages' contents:
       - remove instances of C{/?%(destdir)s} from all man pages
       - C{.so foo.n} becomes a symlink to foo.n
     - (re)compress all man pages with gzip -f -n -9
     - change all symlinks to point to .gz (if they don't already)
     - make all man pages be mode 644
    """
    def _uncompress(self, dirname, names):
        for name in names:
            path = dirname + os.sep + name
            if name.endswith('.gz') and util.isregular(path):
                util.execute('gunzip ' + dirname + os.sep + name)
            if name.endswith('.bz2') and util.isregular(path):
                util.execute('bunzip2 ' + dirname + os.sep + name)

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
                                self.dbg('replacing %s (%s) with symlink %s',
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
                                self.dbg('replacing %s (%s) with symlink %s',
                                          name, match.group(0), target)
                                os.remove(path)
                                os.symlink(target, path)

    def _compress(self, dirname, names):
        for name in names:
            path = dirname + os.sep + name
            if util.isregular(path):
                util.execute('gzip -f -n -9 ' + dirname + os.sep + name)

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

    def do(self):
        for manpath in (
            self.macros.mandir,
            os.sep.join((self.macros.x11prefix, 'man')),
            os.sep.join((self.macros.krbprefix, 'man')),
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
    Properly compress info files and remove dir file; only recipe invocation is
    C{r.NormalizeInfoPages(r.macros.infodir+'/dir')} in the one recipe that
    should own the info dir file.
    """
    def do(self):
        dir = self.macros['infodir']+'/dir'
        fsdir = self.macros['destdir']+dir
        if os.path.exists(fsdir):
            if not self.policyException(dir):
                util.remove(fsdir)
        if os.path.isdir('%(destdir)s/%(infodir)s' %self.macros):
            infofiles = os.listdir('%(destdir)s/%(infodir)s' %self.macros)
            for file in infofiles:
                syspath = '%(destdir)s/%(infodir)s/' %self.macros + file
                path = '%(infodir)s/' %self.macros + file
                if not self.policyException(path):
                    m = self.recipe.magic[path]
                    if not m:
                        # not compressed
                        util.execute('gzip -f -n -9 %s' %syspath)
                        del self.recipe.magic[path]
                    elif m.name == 'gzip' and \
                       (m.contents['compression'] != '9' or \
                        'name' in m.contents):
                        util.execute('gunzip %s; gzip -f -n -9 %s'
                                     %(syspath, syspath[:-3]))
                        del self.recipe.magic[path]
                    elif m.name == 'bzip':
                        # should use gzip instead
                        util.execute('bunzip2 %s; gzip -f -n -9 %s'
                                     %(syspath, syspath[:-4]))
                        del self.recipe.magic[path]


class NormalizeInitscriptLocation(policy.DestdirPolicy):
    """
    Puts initscripts in their place, resolving ambiguity about their
    location.

    Moves all initscripts from /etc/rc.d/init.d/ to their official location
    (if, as is true for the default settings, /etc/rc.d/init.d isn't their
    official location, that is).
    """
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


class NormalizeInitscriptContents(policy.DestdirPolicy):
    """
    Fixes common errors within init scripts, and adds some dependencies
    if needed.
    """
    requires = (
        # for invariantsubtree to be sufficient
        ('NormalizeInitscriptLocation', policy.REQUIRED_PRIOR),
        # for adding requirements
        ('Requires', policy.REQUIRED_SUBSEQUENT),
    )
    invariantsubtrees = [ '%(initdir)s' ]

    def doFile(self, path):
        m = self.recipe.macros
        fullpath = '/'.join((m.destdir, path))
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
    There is some disagreement about where to put X app-defaults
    files; this policy resolves that disagreement, and no exceptions
    are recommended.
    """
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


class NormalizeInterpreterPaths(policy.DestdirPolicy):
    """
    Interpreter paths in scripts vary; this policy re-writes the
    paths, in particular changing indirect calls through env to
    direct calls; exceptions to this policy should only be made
    when it is part of the explicit calling convention of a script
    that the location of the final interpreter depend on the
    user's C{PATH}:
    C{r.NormalizeInterpreterPaths(exceptions=I{filterexp})}
    """
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
            interp = m.contents['interpreter']
            if interp.find('/bin/env') != -1: # finds /usr/bin/env too...
                # rewrite to not have env
                line = m.contents['line']
                # we need to be able to write the file
                os.chmod(d, mode | 0200)
                f = file(d, 'r+')
                l = f.readlines()
                l.pop(0) # we will reconstruct this line, without extra spaces
                wordlist = [ x for x in line.split() ]
                wordlist.pop(0) # get rid of env
                # first look in package
                fullintpath = util.checkPath(wordlist[0], root=destdir)
                if fullintpath == None:
                    # then look on installed system
                    fullintpath = util.checkPath(wordlist[0])
                if fullintpath == None:
                    self.error("Interpreter %s for file %s not found, could not convert from /usr/bin/env syntax", wordlist[0], path)
                    return
                
                wordlist[0] = fullintpath
                l.insert(0, '#!'+" ".join(wordlist)+'\n')
                f.seek(0)
                f.truncate(0) # we may have shrunk the file, avoid garbage
                f.writelines(l)
                f.close()
                # revert any change to mode
                os.chmod(d, mode)
                self.info('changing %s to %s in %s',
                          line, " ".join(wordlist), path)
                del self.recipe.magic[path]


class NormalizePamConfig(policy.DestdirPolicy):
    """
    Some older PAM configuration files include "/lib/security/$ISA/"
    as part of the module path; there is no need for this prefix
    with modern PAM libraries.

    You should never need to run
    C{r.NormalizePamConfig(exceptions=I{filterexp})}
    """
    invariantsubtrees = [
        '%(sysconfdir)s/pam.d/',
    ]

    def doFile(self, path):
        d = util.joinPaths(self.recipe.macros.destdir, path)
        f = file(d, 'r+')
        l = f.readlines()
        l = [x.replace('/lib/security/$ISA/', '') for x in l]
        f.seek(0)
        f.truncate(0) # we may have shrunk the file, avoid garbage
        f.writelines(l)
        f.close()


# Note: NormalizeLibrarySymlinks is in libraries.py
