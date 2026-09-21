.PHONY: all build lint clean validate site serve link-skills help

all: build

help:
	@echo "Available targets:"
	@echo "  make build        Lint every pack, compile catalog.tar.gz (a fraglet), validate it (a fraglet), unpack to catalog/"
	@echo "  make lint         fragletc lint --strict over every pack"
	@echo "  make validate     Validate catalog/ with meta/validate-catalog.py (skills-ref + catalog rules + llms.txt + marketplace + OKF)"
	@echo "  make site         Build, then render the website (a fraglet) from the validated catalog.tar.gz into site/"
	@echo "  make serve        Site, then serve site/ with nginx (docker) on http://localhost:$$PORT (default 8080)"
	@echo "  make link-skills  Build, then symlink catalog/<pack> into ~/.claude/skills/<pack>"
	@echo "  make clean        Remove catalog/, site/ and their archives"

# A pack is a root directory with an index.md. Nothing else is a pack, so the build
# never needs a list: catalog/, static-site/, .github/ have no index.md and are invisible.
PACKS := $(patsubst %/,%,$(dir $(wildcard */index.md)))

# The only host binaries are fragletc and Docker (the documented prerequisites). The
# compiler and the validator are fraglets in meta/: archive in, archive out, because
# fraglets take files, never directory mounts. catalog.tar.gz is validated before it is
# unpacked, so catalog/ only ever holds a catalog that passed; the archive is kept because
# it is the release artifact and the site's input.
SRC_TAR := src.tar.gz
CATALOG_TAR := catalog.tar.gz
SITE_TAR := site.tar.gz
# The canonical host: OKF concepts locate computations by URL there, the site's curl lines use it.
HOST ?= tools.ofthemachine.com
export COPYFILE_DISABLE = 1

build: lint
	@rm -rf catalog $(SRC_TAR) $(CATALOG_TAR)
	tar -czf $(SRC_TAR) index.md CONTRIBUTING.md $(PACKS)
	./meta/compile-catalog.py -p archive=$(SRC_TAR) -p host=$(HOST) --output $(CATALOG_TAR) </dev/null
	@rm -f $(SRC_TAR)
	./meta/validate-catalog.py -p archive=$(CATALOG_TAR) -p strict=true </dev/null
	@mkdir -p catalog && tar -xzf $(CATALOG_TAR) -C catalog

# fragletc owns the header grammar, so fragletc lints it; --strict makes the catalog's
# conventions (every param described, network= declared, when= present) errors too.
lint:
	fragletc lint --strict $(PACKS)

# Re-validate an unpacked catalog/ (build already validated the archive it came from).
validate:
	@rm -f $(CATALOG_TAR) && tar -czf $(CATALOG_TAR) -C catalog .
	./meta/validate-catalog.py -p archive=$(CATALOG_TAR) -p strict=true </dev/null
	@rm -f $(CATALOG_TAR)

# The website is one more projection: the validated catalog.tar.gz in, site.tar.gz out.
# The site root is the catalog root, so every agent URL stays live beside the HTML.
site: build
	./meta/site.py -p archive=$(CATALOG_TAR) -p host=$(HOST) --output $(SITE_TAR) </dev/null
	@mkdir -p site && find site -mindepth 1 -delete && tar -xzf $(SITE_TAR) -C site
	@echo "site/ -> open site/index.html"

# site/ is emptied in place rather than recreated, so a running nginx bind mount survives a rebuild.
PORT ?= 8080
serve: site
	@docker rm -f tools-site >/dev/null 2>&1 || true
	docker run --rm -d --name tools-site -v "$(CURDIR)/site":/usr/share/nginx/html:ro -p $(PORT):80 nginx:alpine >/dev/null
	@echo "http://localhost:$(PORT)  (stop: docker stop tools-site)"

clean:
	rm -rf catalog site $(SRC_TAR) $(CATALOG_TAR) $(SITE_TAR)

# One symlink per pack. Claude Code scans one level under ~/.claude/skills/, and a pack
# directory is a skill directory (SKILL.md at its root). Stale links into this catalog
# from renamed or removed packs are pruned; anything else there is left alone.
CLAUDE_SKILLS_DIR ?= $(HOME)/.claude/skills
link-skills: build
	@mkdir -p "$(CLAUDE_SKILLS_DIR)"
	@for d in catalog/*/; do p=$$(basename $$d); [ -f "$$d/SKILL.md" ] || continue; \
	  ln -sfn "$(CURDIR)/catalog/$$p" "$(CLAUDE_SKILLS_DIR)/$$p"; done
	@for l in "$(CLAUDE_SKILLS_DIR)"/*; do [ -L "$$l" ] && [ ! -e "$$l" ] && \
	  case "$$(readlink "$$l")" in "$(CURDIR)/catalog/"*) rm "$$l";; esac; done; true
	@echo "linked $(words $(PACKS)) packs -> $(CLAUDE_SKILLS_DIR)"
