#!/bin/bash
# tests/test_markdown_to_pdf.sh -- doc/markdown-to-pdf.py across its input shapes
set -eu
cd "$(dirname "$0")/.."
FRAGLETC=${FRAGLETC:-fragletc}
W=$(mktemp -d); trap "rm -rf $W" EXIT
export COPYFILE_DISABLE=1
fail() { echo "FAIL: $*"; exit 1; }
pages() { $FRAGLETC pdf-to-images.py -p pdf_source=$1 -p page=all --output pages.tar.gz=$W/p.tgz >/dev/null 2>&1; tar -tzf $W/p.tgz | grep -c '\.png$'; }

mkdir -p $W/multi/img $W/page
printf '# One note\n\nJust **one** page.\n' > $W/note.md
printf -- '---\ntitle: Chapter One\n---\n\n![dot](img/dot.svg)\n' > $W/multi/01.md
printf '# Chapter Two\n\n| a | b |\n|---|---|\n| 1 | 2 |\n' > $W/multi/02.md
printf '<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80"><circle cx="40" cy="40" r="36" fill="#d9486a"/></svg>' > $W/multi/img/dot.svg
tar -czf $W/multi.tar.gz -C $W/multi .
printf '<style>body{background:#fde68a}</style><h1>EXTRA</h1><img src="dot.svg">' > $W/page/index.html
cp $W/multi/img/dot.svg $W/page/ && tar -czf $W/page.tar.gz -C $W/page .

echo "Testing doc/markdown-to-pdf.py..."
$FRAGLETC markdown-to-pdf.py -p source=$W/note.md --output document.pdf=$W/one.pdf | grep -q "1 page(s), style=reader, toc=no" || fail "single file"
[ "$(pages $W/one.pdf)" = 1 ] || fail "single file should be one page"
$FRAGLETC markdown-to-pdf.py -p source=$W/multi.tar.gz -p title=Digest --output document.pdf=$W/multi.pdf | grep -q "2 page(s), style=reader, toc=yes" || fail "bundle with toc"
[ "$(pages $W/multi.pdf)" = 2 ] || fail "each page of a bundle should start a new PDF page"
$FRAGLETC markdown-to-pdf.py -p source=$W/page.tar.gz -p page=index.html -p style=none --output document.pdf=$W/page.pdf | grep -q "style=none" || fail "verbatim html page"
echo "# Piped" | $FRAGLETC markdown-to-pdf.py --output document.pdf=$W/piped.pdf | grep -q "1 page(s)" || fail "stdin"
if $FRAGLETC markdown-to-pdf.py -p source=$W/multi.tar.gz -p page=missing.md --output document.pdf=$W/x.pdf 2>/dev/null; then fail "missing page should fail"; fi
echo "  ✓ markdown-to-pdf OK"
