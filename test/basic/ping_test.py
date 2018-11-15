import subprocess

PINGOPTS = ['-l3', '-c3', '-q']

def ping_ip_from_host(h, ip):
    cmd = ['mx', h, 'ping'] + PINGOPTS + [ip]
    print('****** ', cmd)
    return subprocess.call(cmd)

# Arguments in pytest are magic:
# * if you declare an argument called p4run, it will take care of p4run for you
#   (and you can use p4run.topo and some utility methods in the tests)
# * the argument controller will run the controller for each switch in the topology
#   (it will use the controller.py in this directory)
def test_ping_works(p4run, controller):
    hosts = p4run.host_IPs()
    for h1 in sorted(hosts):
        for h2 in sorted(hosts):
            for ip in hosts[h2]:
                retcode = ping_ip_from_host(h1, ip)
                assert retcode == 0
