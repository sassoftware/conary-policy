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


VERSION=1.2
NAMEVER=conary-policy-$(VERSION)
DESTDIR=/
POLICYDIR=/usr/lib/conary/policy/

all:

install:
	mkdir -p $(DESTDIR)$(POLICYDIR)
	install -m 644 policy/*.py $(DESTDIR)$(POLICYDIR)

dist:
	if ! grep "^Changes in $(VERSION)" NEWS > /dev/null 2>&1; then \
		echo "no NEWS entry"; \
		1; \
	fi
	$(MAKE) archive

archive:
	mkdir -p $(NAMEVER)/policy
	cp Makefile NEWS LICENSE $(NAMEVER)/
	cp -a doc $(NAMEVER)/
	cp -a policy/*.py $(NAMEVER)/policy/
	tar cjf $(NAMEVER).tar.bz2 $(NAMEVER)
	rm -rf $(NAMEVER)

tag:
	hg tag $(NAMEVER)

version:
	sed -i 's/@NEW@/$(VERSION)/g' NEWS

show-version:
	@echo $(VERSION)

clean:
	rm -f policy/*.pyc
