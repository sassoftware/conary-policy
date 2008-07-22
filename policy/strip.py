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

import errno
import os
import shutil
import stat

from conary.lib import util
from conary.build import macros, policy
from conary.build.use import Use
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


class Strip(policy.DestdirPolicy):
    """
    NAME
    ====

    B{C{r.Strip()}} - Strip debugging information from executables and
    libraries

    SYNOPSIS
    ========

    C{r.Strip([I{filterexp}] I{exceptions=filterexp}])}

    DESCRIPTION
    ===========

    The C{r.Strip()} policy strips executables and libraries of debugging
    information.

    Depending upon configuration, C{r.Strip} may save the debugging
    information for future use.

    EXAMPLES
    ========

    C{r.Strip(exceptions='%(essentiallibdir)s/libpthread-.*.so')}

    This file needs to be handled differently to allow threaded
    debugging, so do not use the C{r.Strip} policy on it.
    """
    processUnmodified = False
    invariantinclusions = [
        ('%(bindir)s/', None, stat.S_IFDIR),
        ('%(essentialbindir)s/', None, stat.S_IFDIR),
        ('%(sbindir)s/', None, stat.S_IFDIR),
        ('%(essentialsbindir)s/', None, stat.S_IFDIR),
        ('%(x11prefix)s/bin/', None, stat.S_IFDIR),
        ('%(krbprefix)s/bin/', None, stat.S_IFDIR),
        ('%(libdir)s/', None, stat.S_IFDIR),
        ('%(essentiallibdir)s/', None, stat.S_IFDIR),
        # we need to strip these separately on a multilib system, and
        # on non-multilib systems the multiple listing will be ignored.
        ('%(prefix)s/lib/', None, stat.S_IFDIR),
        ('/lib/', None, stat.S_IFDIR),
    ]
    invariantexceptions = [
        # let's not recurse...
        '%(debugsrcdir)s/',
        '%(debuglibdir)s/',
    ]

    def __init__(self, *args, **keywords):
        policy.DestdirPolicy.__init__(self, *args, **keywords)
        self.tryDebuginfo = True
        self.db = None

    def updateArgs(self, *args, **keywords):
        self.debuginfo = False
        self.tryDebuginfo = keywords.pop('debuginfo', True)
        policy.DestdirPolicy.updateArgs(self, *args, **keywords)

    def test(self):
        # stripping bootstrap builds just makes debugging harder,
        # as debuginfo is generally not available in boostrap builds
        return not Use.bootstrap._get()

    def preProcess(self):
        self.invariantsubtrees = [x[0] for x in self.invariantinclusions]
        # see if we can do debuginfo
        self.debuginfo = False
        # we need this for the debuginfo case
        self.dm = macros.Macros()
        self.dm.update(self.macros)
        # we need to start searching from just below the build directory
        topbuilddir = '/'.join(self.macros.builddir.split('/')[:-1])
        if self.tryDebuginfo and\
           'eu-strip' in self.macros.strip and \
           'debugedit' in self.macros and \
           util.checkPath(self.macros.debugedit):
            if len(self.macros.debugsrcdir) > len(topbuilddir):
                # because we have to overwrite fixed-length strings
                # in binaries, we need to ensure that the value being
                # written is no longer than the existing value to
                # avoid corrupting the binaries
                raise RuntimeError('insufficient space in binaries'
                    ' for path replacement, add %d characters to buildPath'
                    % (len(self.macros.debugsrcdir) - len(topbuilddir)))
            self.debuginfo = True
            self.debugfiles = set()
            self.dm.topbuilddir = topbuilddir

    def _openDb(self):
        if not self.db:
            self.db = database.Database(self.recipe.cfg.root,
                                   self.recipe.cfg.dbPath)

    def doFile(self, path):
        m = self.recipe.magic[path]
        if not m:
            return
        # FIXME: should be:
        #if (m.name == "ELF" or m.name == "ar") and \
        #   m.contents['hasDebug']):
        # but this has to wait until ewt writes debug detection
        # for archives as well as elf files
        if (m.name == "ELF" and m.contents['hasDebug']) or \
           (m.name == "ar"):
            oldmode = None
            fullpath = self.dm.destdir+path
            mode = os.lstat(fullpath)[stat.ST_MODE]
            if mode & 0600 != 0600:
                # need to be able to read and write the file to strip it
                oldmode = mode
                os.chmod(fullpath, mode|0600)
            if self.debuginfo and m.name == 'ELF' and not path.endswith('.o'):

                dir=os.path.dirname(path)
                b=os.path.basename(path)
                if not b.endswith('.debug'):
                    b += '.debug'

                debuglibdir = '%(destdir)s%(debuglibdir)s' %self.dm +dir
                debuglibpath = util.joinPaths(debuglibdir, b)
                if os.path.exists(debuglibpath):
                    return

                self._openDb()
                _findProgPath(self.macros.debugedit, self.db, self.recipe)

                # null-separated AND terminated list, so we need to throw
                # away the last (empty) item before updating self.debugfiles
                self.debugfiles |= set(util.popen(
                    '%(debugedit)s -b %(topbuilddir)s -d %(debugsrcdir)s'
                    ' -l /dev/stdout '%self.dm
                    +fullpath).read().split('\x00')[:-1])
                util.mkdirChain(debuglibdir)
                util.execute('%s -f %s %s' %(
                    self.dm.strip, debuglibpath, fullpath))

            else:
                self._openDb()
                if m.name == 'ar' or path.endswith('.o'):
                    # just in case strip is eu-strip, which segfaults
                    # whenever it touches an ar archive, and seems to
                    # break some .o files
                    _findProgPath(self.macros.strip_archive, self.db, self.recipe)
                    util.execute('%(strip_archive)s ' %self.dm +fullpath)
                else:
                    _findProgPath(self.macros.strip, self.db, self.recipe)
                    util.execute('%(strip)s ' %self.dm +fullpath)

            del self.recipe.magic[path]
            if oldmode is not None:
                os.chmod(fullpath, oldmode)

    def postProcess(self):
        if self.debuginfo:
            for filename in sorted(self.debugfiles):
                builddirpath = '%(topbuilddir)s/' % self.dm +filename
                dir = os.path.dirname(filename)
                util.mkdirChain('%(destdir)s%(debugsrcdir)s/'%self.dm +dir)
                try:
                    targetfile = '%(destdir)s%(debugsrcdir)s/'%self.dm +filename
                    shutil.copy2(builddirpath, targetfile)
                    # these files only need to be readable; avoid warnings
                    # about group-writeable files, etc.
                    os.chmod(targetfile, 0644)
                except IOError, msg:
                    if msg.errno == errno.ENOENT:
                        pass
                    else:
                        raise
