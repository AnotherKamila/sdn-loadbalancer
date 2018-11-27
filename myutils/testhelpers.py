import subprocess
import time

def run_on_host(host, cmd, background=False):
    realcmd = ['mx', host] + cmd
    print(' ****** ', realcmd, ' ****** ')
    if not background:
        return subprocess.call(realcmd)
    else:
        return subprocess.Popen(
            realcmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )

def test_all_host_pairs(hosts, testfn):
    for client in sorted(hosts):
        for server in sorted(hosts):
            serverip = hosts[server]
            testfn(client, server, serverip)


PINGOPTS = ['-l3', '-c3', '-q']

def ping_ip_from_host(h, ip, ping6=False):
    ping = 'ping6' if ping6 else 'ping'
    assert run_on_host(h, [ping] + PINGOPTS + [ip]) == 0

def ping_all(hosts, ping6=False):
    """Pings all pairs of hosts in a Mininet emulator.

    Hosts: dict of hostname => IP
    """
    test_all_host_pairs(hosts, lambda h, _, ip: ping_ip_from_host(h, ip, ping6))


def netcat_from_to(client, server, serverip, port=4742):
    # Skip if on localhost, because for some reason this sometimes
    # breaks and I don't want to deal with this.
    if client == server: return

    servercmd = ['nc', '-l', str(port)]
    clientcmd = ['nc', serverip, str(port)]
    server = run_on_host(server, servercmd, background=True)
    time.sleep(1)  # give it time to bind
    client = run_on_host(client, clientcmd, background=True)

    out, _ = client.communicate('hello')
    print('*** OUT ', out)
    print('*** RET ', client.returncode)
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
