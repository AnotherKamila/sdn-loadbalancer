from myutils import ping_all, netcat_all

def test_ping_ipv4(p4run, controller):
    ping_all(p4run.host_IPs())

def test_netcat(p4run, controller):
    netcat_all(p4run.host_IPs())
