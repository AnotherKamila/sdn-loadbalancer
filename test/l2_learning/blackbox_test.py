from myutils.testhelpers import ping_all, netcat_all

# Arguments in pytest are magic:
# * if you declare an argument called p4run, it will take care of p4run for you
#   (and you can use p4run.topo and some utility methods in the tests)
# * the argument controller will run the controller for each switch in the topology
#   (it will use the controller.py in this directory)
def test_ping_ipv4(p4run, controller):
    ping_all(p4run.host_IPs())

def test_netcat(p4run, controller):
    netcat_all(p4run.host_IPs())
