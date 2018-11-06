import subprocess

# TODO this could be discovered by topology
hosts = {
    "h1": "10.0.0.1",
    "h2": "10.0.0.2",
    "h3": "10.0.0.3",
    "h4": "10.0.0.4",
}

def ping_from_to(h1, h2):
    cmd = ['mx', h1, 'ping', '-c1', hosts[h2]]
    return subprocess.run(cmd)

def test_ping_works():
    for h1 in sorted(hosts.keys()):
        for h2 in sorted(hosts.keys()):
            ping = ping_from_to(h1, h2)
            assert ping.returncode == 0
