NAME = script.elementum.burst
GIT = git
GIT_VERSION = $(shell $(GIT) describe --abbrev=0 --tags)
GIT_USER = elgatito
GIT_REPOSITORY = script.elementum.burst
TAG_VERSION = $(subst v,,$(GIT_VERSION))
LAST_COMMIT = $(shell $(GIT) log -1 --pretty=\%B)
VERSION = $(shell sed -ne "s/.*COLOR\]\"\sversion=\"\([0-9a-z\.\-]*\)\".*/\1/p" addon.xml)
ZIP_SUFFIX = zip
ZIP_FILE = $(NAME)-$(VERSION).$(ZIP_SUFFIX)

all: clean zip

$(ZIP_FILE):
	$(GIT) archive --format zip --prefix $(NAME)/ --output $(ZIP_FILE) HEAD
	rm -rf $(NAME)

zip: $(ZIP_FILE)

clean_arch:
	 rm -f $(ZIP_FILE)

clean:
	rm -f $(ZIP_FILE)
	rm -rf $(NAME)

# extract:
# 	./scripts/extract.py --exclude-icons
#
# extract-icons:
# 	./scripts/extract.py --exclude-defs

upload:
	$(eval EXISTS := $(shell github-release info --user $(GIT_USER) --repo $(GIT_REPOSITORY) --tag v$(VERSION) 1>&2 2>/dev/null; echo $$?))
ifneq ($(EXISTS),1)
	github-release release \
		--user $(GIT_USER) \
		--repo $(GIT_REPOSITORY) \
		--tag v$(VERSION) \
		--name "$(VERSION)" \
		--description "$(VERSION)"
endif

	github-release upload \
		--user $(GIT_USER) \
		--repo $(GIT_REPOSITORY) \
		--replace \
		--tag v$(VERSION) \
		--file $(NAME)-$(VERSION).zip \
		--name $(NAME)-$(VERSION).zip

settings:
	scripts/generate_settings.py

locales:
	scripts/xgettext_merge.sh