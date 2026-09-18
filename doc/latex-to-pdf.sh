#!/usr/bin/env -S fragletc --image ofthemachine/latex@sha256:add4f310e2fb92ebeeb7bc7fa5a95f920fa78adabcc8565301bbb178eac2a0b3
#: d=Compile a LaTeX document to PDF (full TeX Live, offline, deterministic -- no runtime package fetching). Mounts input TeX file via fragletc file-shaped param (:file) to /input/tex_source.
#: when=Use when the user has LaTeX source and wants the compiled PDF.
#: network=none
#: stdin=none
#: param=tex_source:required:file:d=TeX source mounted at /input/tex_source
#: param=engine:default=pdflatex:description=TeX engine: pdflatex, xelatex, or lualatex
#: output=paper.pdf

case "${ENGINE}" in
  xelatex)  FLAG=-xelatex  ;;
  lualatex) FLAG=-lualatex ;;
  *)        FLAG=-pdf      ;;
esac
latexmk "$FLAG" -interaction=nonstopmode -halt-on-error \
  -jobname=paper -output-directory=/output "$TEX_SOURCE"
