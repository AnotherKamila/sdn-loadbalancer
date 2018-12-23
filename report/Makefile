
NOTE  = !! change the next line to fit your filename; no spaces at file name end !!
FILE  = report

all:
	xelatex $(FILE)
	bibtex $(FILE)
	xelatex $(FILE)
	xelatex $(FILE)

clean:
	rm -f *.dvi *.log *.aux *.bbl *.blg *.toc *.lof *.lot *.cb *.~ *.out *.fdb_latexmk *.fls
