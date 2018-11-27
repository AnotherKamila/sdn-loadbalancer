import subprocess

from myutils.testhelpers import netcat_from_to

def hostport(s):
    return s.split(':')

def test_addr_rewriting(p4run, controller, pools):
    netcat_from_to('h4', 'h1', '10.0.1.1', port=7000)
