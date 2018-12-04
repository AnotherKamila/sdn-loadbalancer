from __future__ import print_function

import subprocess
import os
import signal
import time

def run_cmd(cmd, host=None, background=False):
    if host: cmd = ['mx', host] + cmd
    realcmd = [str(a) for a in cmd]
    print(' ****** ', ' '.join(realcmd), ' ****** ')
    if not background:
        return subprocess.call(realcmd)
    else:
        return subprocess.Popen(
            realcmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            preexec_fn=os.setsid,
        )

# what the fuckity fuck why is this so difficult
def kill_with_children(process):
    return run_cmd([
        'sudo', 'kill', '-SIGTERM', '--', '-{}'.format(os.getpgid(process.pid))
    ])


def test_all_host_pairs(hosts, testfn):
    for client in sorted(hosts):
        for server in sorted(hosts):
            serverip = hosts[server]
            testfn(client, server, serverip)


PINGOPTS = ['-l3', '-c3', '-q']

def ping_ip_from_host(h, ip, ping6=False):
    ping = 'ping6' if ping6 else 'ping'
    assert run_cmd([ping] + PINGOPTS + [ip], h) == 0

def ping_all(hosts, ping6=False):
    """Pings all pairs of hosts in a Mininet emulator.

    Hosts: dict of hostname => IP
    """
    test_all_host_pairs(hosts, lambda h, _, ip: ping_ip_from_host(h, ip, ping6))


def netcat_server(host, port=4742, options=None):
    if options == None: options = []
    server = run_cmd(['nc'] + options + ['-l', str(port)], host, background=True)
    time.sleep(0.5)  # give it time to bind
    return server

def netcat_client(host, server_ip, port=4742):
    return run_cmd(['nc', server_ip, str(port)], host, background=True)

def netcat_from_to(client_host, server_host, server_ip, port=4742):
    # Skip if on localhost, because for some reason this sometimes
    # breaks and I don't want to deal with this.
    if client_host == server_host: return

    server = netcat_server(server_host, port)
    client = netcat_client(client_host, server_ip, port)

    out, _ = client.communicate('hello')
    assert out == ''
    assert client.returncode == 0

    out, _ = server.communicate()
    assert out == 'hello'
    assert server.returncode == 0

def netcat_all(hosts):
    """Netcats between all pairs of hosts in a Mininet emulator.

    Hosts: dict of hostname => IP
    """
    test_all_host_pairs(hosts, netcat_from_to)
