MAIN=main
LATEX=pdflatex

.PHONY: all pdf clean

all: pdf

pdf:
	$(LATEX) $(MAIN).tex
	$(LATEX) $(MAIN).tex

clean:
	rm -f $(MAIN).aux $(MAIN).log $(MAIN).out $(MAIN).toc \
	       $(MAIN).bbl $(MAIN).blg $(MAIN).lof $(MAIN).lot
