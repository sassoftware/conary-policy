#
# Copyright (c) SAS Institute Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


import re
import types

from conary.build import policy

class TagLocale(policy.PackagePolicy):
    """
    NAME
    ====

    B{C{r.TagLocale()}} - Tags locale files based on path

    SYNOPSIS
    ========

    C{r.TagLocale([I{filterexp}] || [I{exceptions=filterexp}] || localeExp=localExpression)}

    DESCRIPTION
    ===========

    The C{r.TagLocale()} policy tags files according to their
    locale as C{locale(I{localename})}, choosing C{I{localname}}
    from the file path.  Exceptions to the policy are passed in via
    C{r.TagLocale(I{exceptions=filterexpression})} and are
    expressed in terms of file names.

    Additional expressions for tagging locale-specific files can be
    passed in with the C{localeExp} keyword argument.  This is a
    string or list or tuple of strings, where each string is a
    regular expression which has at least one non-optional match
    group which is the first match group, and which specifies the
    name of the locale.

    EXAMPLES
    ========

    C{r.TagLocale(exceptions='/')}

    Effectively disables the C{TagLocale} policy.

    C{r.TagLocale(exceptions='/usr/share/local/zzz/broken')}

    Do not tag the file C{/usr/share/local/zzz/broken} as C{locale(zzz)}.

    C{r.TagLocale(localeExp=r'/some/path/(?P<locale>.*).locale.messages')

    Tags the file /some/path/pt.locale.messages as locale(pt)
    and the file /some/path/en.locale.messages as locale(en).
    There must be exactly one named group named "C{locale}"; do
    do this specify the locale using C{(?P<locale>...)} in the
    regular expression.
    """

    requires = (
        ('PackageSpec', policy.REQUIRED_PRIOR),
    )
    # changing (or adding) locale tagging might be *the* reason for a
    # derived package
    processUnmodified = True
    invariantexceptions = [ '(%(debuglibdir)s|%(debugsrcdir)s)/', ]
    filetree = policy.PACKAGE
    localeExpressions = [
        re.compile(r'.*/locale(?:s)?/(?P<locale>[a-z]{2,3}(?:_[a-zA-Z]{2,3})?)(?:(?:\@|\.).*)?/.*/'),
        re.compile(r'.*/locale/man/(?P<locale>[a-z]{2,3})'),
        re.compile(r'/usr/share/man/(?P<locale>(?!man|cat|whatis|web)[a-zA-Z]{2,3}(?:_[a-z]{2,3})?).*/.*'),
    ]
    legalLocaleName = re.compile(r'^[a-zA-Z_]*$')

    def addLocaleExpression(self, exp):
        if '(?P<locale>' in exp:
            self.localeExpressions.append(re.compile(exp))
        else:
            self.warn('localeExp "%s" missing named group "locale";'
                      ' use "(?P<locale>" to introduce named group', exp)

    def updateArgs(self, *args, **keywords):
        localeExp = keywords.pop('localeExp', None)
        if isinstance(localeExp, (list, tuple, set)):
            for localeInstance in localeExp:
                self.addLocaleExpression(localeInstance)
        elif isinstance(localeExp, types.StringTypes):
            self.addLocaleExpression(localeExp)
        policy.PackagePolicy.updateArgs(self, *args, **keywords)

    def doFile(self, filename):
        if hasattr(self.recipe, '_getCapsulePathsForFile'):
            if self.recipe._getCapsulePathsForFile(filename):
                # even if a capsule were called :locale we still could
                # not do locale filtering on it
                return

        for localeExp in self.localeExpressions:
            m = localeExp.match(filename)
            if m is not None:
                groupdict = m.groupdict()
                if 'locale' in groupdict:
                    locale = m.groupdict()['locale']
                    self._tagLocale(filename, locale)

    def _tagLocale(self, filename, locale):
        if self.legalLocaleName.match(locale) is None:
            self.warn('locale "%s" for file %s includes disallowed characters',
                      locale, filename)
            return
        componentMap = self.recipe.autopkg.componentMap
        if filename not in componentMap:
            return
        pkg = componentMap[filename]
        componentName = pkg.name.split(':')[1]
        if componentName not in set(('locale', 'doc', 'supdoc')):
            self.warn('locale "%s" for file %s in non-locale :%s component,'
                      ' not adding "locale(%s)" tag',
                      locale, filename, componentName, locale)
            return
        f = pkg.getFile(filename)
        f.tags.set('locale(%s)' %locale)
