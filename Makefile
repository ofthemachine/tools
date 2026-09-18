.PHONY: all build lint clean validate link-skills help

all: build

help:
	@echo "Available targets:"
	@echo "  make build        Lint every pack, compile catalog.tar.gz (a fraglet), validate it (a fraglet), unpack to catalog/"
	@echo "  make lint         fragletc lint --strict over every pack"
	@echo "  make validate     Validate catalog/ with meta/validate-catalog.py (skills-ref + catalog rules + llms.txt + marketplace + OKF)"
	@echo "  make link-skills  Build, then symlink catalog/<pack> into ~/.claude/skills/<pack>"
	@echo "  make clean        Remove catalog/"

# A pack is a root directory with an index.md. Nothing else is a pack, so the build
# never needs a list: catalog/, static-site/, .github/ have no index.md and are invisible.
PACKS := $(patsubst %/,%,$(dir $(wildcard */index.md)))

# The only host binaries are fragletc and Docker (the documented prerequisites). The
# compiler and the validator are fraglets in meta/: archive in, archive out, because
# fraglets take files, never directory mounts. catalog.tar.gz is validated before it is
# unpacked, so catalog/ only ever holds a catalog that passed.
SRC_TAR := src.tar.gz
CATALOG_TAR := catalog.tar.gz
export COPYFILE_DISABLE = 1

build: lint
	@rm -rf catalog $(SRC_TAR) $(CATALOG_TAR)
	tar -czf $(SRC_TAR) index.md $(PACKS)
	./meta/compile-catalog.py -p archive=$(SRC_TAR) --output $(CATALOG_TAR) </dev/null
	@rm -f $(SRC_TAR)
	./meta/validate-catalog.py -p archive=$(CATALOG_TAR) -p strict=true </dev/null
	@mkdir -p catalog && tar -xzf $(CATALOG_TAR) -C catalog && rm -f $(CATALOG_TAR)

# fragletc owns the header grammar, so fragletc lints it; --strict makes the catalog's
# conventions (every param described, network= declared, when= present) errors too.
lint:
	fragletc lint --strict $(PACKS)

# Re-validate an unpacked catalog/ (build already validated the archive it came from).
validate:
	@rm -f $(CATALOG_TAR) && tar -czf $(CATALOG_TAR) -C catalog .
	./meta/validate-catalog.py -p archive=$(CATALOG_TAR) -p strict=true </dev/null
	@rm -f $(CATALOG_TAR)

clean:
	rm -rf catalog $(SRC_TAR) $(CATALOG_TAR)

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
