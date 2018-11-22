import subprocess

PINGOPTS = ['-l3', '-c3', '-q']

# TODO split these functions into something shareable

def test_ping_ipv4(p4run, controller):
    ping_all(p4run.host_IPs())

def ping_ip_from_host(h, ip, ping6=False):
    ping = 'ping6' if ping6 else 'ping'
    cmd = ['mx', h, ping] + PINGOPTS + [ip]
    print('****** ', cmd)
    return subprocess.call(cmd)

def ping_all(hosts, ping6=False):
    for h1 in sorted(hosts):
        for h2 in sorted(hosts):
            ip = hosts[h2]
            retcode = ping_ip_from_host(h1, ip, ping6)
            assert retcode == 0
