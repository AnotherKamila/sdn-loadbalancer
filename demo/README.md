# Demo

Run `p4run` separately (there is a `p4app.json` here).

Run `gnuplot ./graph.gnuplot` to see the graph of loads and weights over time. This can also be run outside of the VM if the folder is synced. The demo will write data into `./data.tsv`, and `graph.gnuplot` will display it live.

Run `./main.py` to start the demo. Press Enter once to start the load-generating clients. Press Enter again to start the weights adjustment loop. (Make sure to `. ../.env` before running it.)
