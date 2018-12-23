# sdn-loadbalancer

L4 load balancer that can dynamically change the distribution for load balancing.

Current implementation allows for weighing based on server metrics such as request latency or server load (and this is easy to change).

I use the [Twisted](https://twistedmatrix.com/) framework for the controller and tests. See `./twisted-intro.md` for a very quick run through things you need to know to read the code here.

## What's in here

In approximate order of interestingness:

* `p4src`: the code for the switches (data plane)
* `controller`: the code for the network controller (control plane)
* `test`: Integration tests for the various components
* `demo`: runs the controller and a few servers + clients, showcases the load balancing
* `presentation`: slides + assets for the presentation
* `report`: the report
* `myutils`: random Python utility functions, plus a stand-alone server & client

See the README files inside the directories for information about the specific parts.

## How to run everything in here

### P4 stuff

The `demo/` directory and the various subdirectories under `/test` contain an example `p4app.json` and more documentation.

Note that the switch won't be able to cope with a lot of connections if it has debugging enabled. Therefore, for the demo and most tests it is needed to re-compile the switch without debugging:

```
su - p4
cd ~/p4-tools/
git clone https://github.com/p4lang/behavioral-model.git bmv2-opt
cd bmv2-opt
git checkout 7e71a9bdd161afd63a162aaa96703bfa7ab1b3e1
./autogen.sh
./configure --disable-elogger --disable-logging-macros 'CFLAGS=-g -O2' 'CXXFLAGS=-g -O2'
make -j 2
sudo make install
sudo ldconfig
```

### Python

The controller needs to be able to use raw sockets (to receive the cloned packets from the controller). To run it as non-root, the Python executable needs to get the `net_raw` capability. Set it using:

```sh
$ sudo setcap cap_net_raw=eip $(readlink -f $(which python))
```

#### Global install: No virtualenv

Install the dependencies, add current directory to PYTHONPATH, and source `.env`:
```sh
$ sudo pip2 install attrs twisted pytest pytest-twisted
$ ./fix-pythonpath.sh
$ . .env
$ pytest  # for example
```

Remember that the `.env` file must always be sourced, to get the right PYTHONPATH.

#### Virtualenv install [more complicated => probably ignore this and install globally]

TODO flag for pipenv to install with site packages

##### TL;DR

Assuming this repository has been cloned to `my-repo`:

```sh
$ sudo pip2 install pipenv
$ cd my-repo
$ ./fix-pythonpath.sh
$ pipenv sync
$ # upgrade system packages if it complains: sudo pip2 install --upgrade six (see below)
$ pipenv shell
$ pipenv sync  # must be run again in the shell for some reason (pipenv/pytest bug)
$ pytest  # for example
```
##### Python path

The root of the repo needs to be in the Python path.

The easiest way to achieve that is to run `./fix-pythonpath.sh` in the root of the repo right after cloning it. This will change `PYTHONPATH` in the `.env` file. (`pipenv` sources the `.env` automatically.)

##### Virtual env

I use `pipenv` to manage the dependencies/virtualenvs. Assuming you have `pip2`, install `pipenv` and then let it install dependencies using:

```sh
sudo pip2 install pipenv
pipenv sync
pipenv run pipenv sync  # must be run again in the shell for some reason (pipenv/pytest bug)
```

If you run `pipenv` without `sudo`, it may fail because of conflicting packages in the base system. If that happens, upgrade the problematic package before running `pipenv`. Example:

```
$ pipenv sync
...
[pipenv.exceptions.InstallError]: ["Could not install packages due to an EnvironmentError: [Errno 13] Permission denied: '/usr/local/lib/python2.7/dist-packages/six-1.11.0.dist-info/DESCRIPTION.rst'", 'Consider using the `--user` option or check the permissions.']
$ # ^^ Notice: it's complaining about six.
$ sudo pip2 install --upgrade six  # fix it
$ pipenv sync  # try again
```

Then run everything inside a `pipenv shell` to get the virtualenv set up.
