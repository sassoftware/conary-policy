#
# Copyright (c) 2008 rPath, Inc.
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

from conary.build import policy

class _BaseMetadata(policy.PackagePolicy):
    keywords = {
        'language'      : None,
        'troveNames'    : None,
        'macros'        : True,
    }

    def __init__(self, recipe, *args, **keywords):
        policy.PackagePolicy.__init__(self, recipe, *args, **keywords)
        self.applymacros = self.macros

    def updateArgs(self, *args, **keywords):
        policy.PackagePolicy.updateArgs(self, *args, **keywords)
        self.applymacros = self.macros

    def _getTroveNames(self):
        # Build a map of troves that we have available
        availTroveNames = set(x.name
                              for x in self.recipe.autopkg.getComponents())
        availTroveNames.update(set(self.recipe.packages))

        # If no trove names were supplied, apply the metadata to all packages
        troveNamesArg = ((self.troveNames is None and self.recipe.packages) or
                                                            self.troveNames)
        troveNames = []
        for troveName in troveNamesArg:
            # Check to see if the :component syntax was used
            if not troveName.startswith(':'):
                if troveName not in availTroveNames:
                    # We don't know about this trove name, just move on
                    continue
                troveNames.append(troveName)
                continue
            # The trove spec starts with :. Extract all troves that have that
            # component.
            for pkgName in self.recipe.packages:
                if pkgName + troveName in availTroveNames:
                    troveNames.append(pkgName + troveName)
        return troveNames

class Description(_BaseMetadata):
    """
    NAME
    ====

    B{C{r.Description()}} - Set the description for the troves built from the
    recipe.

    SYNOPSIS
    ========

    C{r.Description([I{shortDesc}=,] [I{longDesc}=,] [I{language}=,] [I{troveNames}=,] [I{macros=}])}

    DESCRIPTION
    ===========

    The C{r.Description()} class adds description strings to troves.

    If the keyword argument I{troveNames} is not specified, all packages built
    out of the source component will be assigned the specified short
    description and/or long description.

    If I{troveNames} is specified, it should be a list of strings.

    Normally, descriptions should not be attached to individual components of
    a trove. However, it is possible to specify components in the I{troveNames}
    list. It is also possible to designate just the component by prefixing it
    with a colon (:) character, in which case all components with that name
    from all packages will have the description.

    The I{shortDesc} and I{longDesc} keyword arguments can be used to specify
    the short description and the long description, respectively.

    If a language is specified with keyword argument I{language}, the strings
    will be associated to that language, otherwise the default language will
    be used.

    The C{macros} keyword accepts a boolean value, and defaults
    to True. If the value of C{macros} is False, recipe macros in the
    description strings will not be interpolated.

    EXAMPLES
    ========

    Assuming that the source trove will build two packages, I{prk-client} and
    I{prk-server}, each with I{:runtime} and I{:lib} components:

    C{r.Description(shortDescription = "PRK implementation for Linux", "This is the implementation of PRK for Linux")}

    will set the descriptions for the I{prk-client} and I{prk-server} troves.

    C{r.Description(shortDescription = "Runtime component for PRK", "This is the runtime component for prk", troveNames = [ ':runtime' ])}

    will set the descriptions for the I{prk-client:runtime} and
    I{prk-server:runtime} troves.
    """

    keywords = _BaseMetadata.keywords.copy()
    keywords.update({
        'shortDesc'     : None,
        'longDesc'      : None,
    })

    def do(self):
        troveNames = self._getTroveNames()
        itemTups = ((x, getattr(self, x)) for x in
                                    ['shortDesc', 'longDesc', 'language'])
        if self.applymacros:
            itemDict = dict((x, y % self.recipe.macros) for (x, y) in itemTups)
        else:
            itemDict = dict(itemTups)
        self.recipe._addMetadataItem(troveNames, itemDict)

class Licenses(_BaseMetadata):
    """
    NAME
    ====

    B{C{r.Licenses()}} - Set the description for the troves built from the
    recipe.

    SYNOPSIS
    ========

    C{r.Licenses(I{license}, [I{license}, ...] [I{language}=,] [I{troveNames}=,] [I{macros=}])}

    DESCRIPTION
    ===========

    The C{r.Licenses()} class adds license information to troves.

    If the keyword argument I{troveNames} is not specified, all packages built
    out of the source component will be assigned the specified license
    information.

    If I{troveNames} is specified, it should be a list of strings.

    It is possible to specify both packages and components in the I{troveNames}
    list. It is also possible to designate just the component by prefixing it
    with a colon (:) character, in which case all components with that name
    from all packages will have the license.

    If a language is specified with keyword argument I{language}, the strings
    will be associated to that language, otherwise the default language will
    be used.

    The C{macros} keyword accepts a boolean value, and defaults
    to True. If the value of C{macros} is False, recipe macros in the
    license strings will not be interpolated.

    EXAMPLES
    ========

    Assuming that the source trove will build two packages, I{prk-client} and
    I{prk-server}, each with I{:runtime} and I{:lib} components:

    C{r.License(['GPL', 'LGPL'])}

    will set the licenses for the I{prk-client} and I{prk-server} troves.

    C{r.Licenses(['GPL', 'LGPL'], troveNames = [ ':runtime' ])}

    will set the licenses for the I{prk-client:runtime} and
    I{prk-server:runtime} troves.
    """

    def updateArgs(self, *args, **keywords):
        self.licenses = args
        _BaseMetadata.updateArgs(self, **keywords)

    def do(self):
        troveNames = self._getTroveNames()
        if self.applymacros:
            licenses = [x % self.recipe.macros for x in self.licenses]
        else:
            licenses = self.licenses
        itemDict = dict(licenses = licenses, language = self.language)
        self.recipe._addMetadataItem(troveNames, itemDict)
