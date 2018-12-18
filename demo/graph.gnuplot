set term x11 enhanced font 'bitstream charter,28' lw 4

set multiplot layout 2,1
set xlabel 'time / seconds'
set xrange [0:120]
# set yrange [0:*]

set title '{/=32 Weights}'
set yrange [0:10]
plot 'data.tsv' using 1:2  with lines title '1 CPU' , \
     ''         using 1:3  with lines title '2 CPUs', \
     ''         using 1:4  with lines title '4 CPUs' lc "blue", \
     ''         using 1:5  with lines title '6 CPUs' lc "#B03060"

set title '{/=32 Loads}'
set yrange [0:10]
plot 'data.tsv' using 1:6  with lines title '1 CPU', \
     ''         using 1:7  with lines title '2 CPUs', \
     ''         using 1:8  with lines title '4 CPUs' lc "blue", \
     ''         using 1:9  with lines title '6 CPUs' lc "#B03060"

# set yrange [0:24]
# set title 'conns'
# plot 'data.tsv' using 1:10 with lines , \
#      ''         using 1:11 with lines , \
#      ''         using 1:12 with lines , \
#      ''         using 1:13 with lines 

pause 0.2
unset multiplot
reread
