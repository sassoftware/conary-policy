Conary Policy
=============
 
Overview
--------
This repository holds the default set of build-time policies used by Conary.
Policies are pluggable actions executed in the last phase of a Conary build to
inspect and modify the state of the package according to predetermined rules.
These rules may normalize the package in order to conform to particular
filesystem layouts, scan for provided and required dependencies, and check for
fatal problems or broken linkages.

For more information about policies in general, see doc/PluggablePolicy

The testsuite for conary-policy is found in the "conary" repository.
