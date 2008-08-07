#
# Copyright (c) 2004-2008 rPath, Inc.
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

VERSION=1.0.19
NAMEVER=conary-policy-$(VERSION)
DESTDIR=/
POLICYDIR=/usr/lib/conary/policy/

all:

install:
	mkdir -p $(DESTDIR)$(POLICYDIR)
	install -m 644 policy/*.py $(DESTDIR)$(POLICYDIR)

dist:
	mkdir -p $(NAMEVER)/policy
	cp Makefile NEWS LICENSE $(NAMEVER)/
	cp -a doc $(NAMEVER)/
	cp -a policy/*.py $(NAMEVER)/policy/
	tar cjf $(NAMEVER).tar.bz2 $(NAMEVER)
	rm -rf $(NAMEVER)

tag:
	hg tag $(NAMEVER)

clean:
	rm -f policy/*.pyc
