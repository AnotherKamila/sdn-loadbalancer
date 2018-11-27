from myutils import ping_all, netcat_all

def test_ping_dips(p4run, controller):
    ping_all(p4run.host_IPs())

def test_netcat_dips(p4run, controller):
    netcat_all(p4run.host_IPs())
