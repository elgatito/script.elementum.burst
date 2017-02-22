NAME = script.quasar.burst
GIT = git
GIT_VERSION = $(shell $(GIT) describe --abbrev=0 --tags)
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

extract:
	./scripts/extract.py --exclude-icons

extract-icons:
	./scripts/extract.py --exclude-defs

bump:
	sed -i "s/COLOR\]\" version=\"\([0-9a-z\.\-]*\)\"/COLOR\]\" version=\"${TAG_VERSION}\"/" addon.xml
	$(GIT) reset --soft @{1}
	$(GIT) add addon.xml
	$(GIT) commit -m "${LAST_COMMIT}"
	$(GIT) tag -f $(GIT_VERSION)

surge:
	$(GIT) clone --depth=1 https://bitbucket.com/scakemyer/burst-website.git
	sed -i "s/version\s=\s\"\([0-9a-z\.\-]*\)\"/version = \"${VERSION}\"/" burst-website/public/index.jade
	cd burst-website && harp compile . html/
	mkdir -p burst-website/html/release/
	cp addon.xml changelog.txt icon.png fanart.jpg burst-website/html/release/
	cp *.zip burst-website/html/release/
	cd burst-website && surge html burst.surge.sh

docs-init:
	cd docs && sphinx-apidoc --no-toc -M -o source/ ../burst

docs-dev:
	cd docs && sphinx-autobuild . _build_dev
	rm -rf docs/_build_dev

docs:
	cd docs && make html
