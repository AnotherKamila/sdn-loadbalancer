# sdn-loadbalancer

L4 load balancer that can dynamically change the distribution for load balancing.

Current implementation allows for weighing based on server metrics such as request latency or server load (and this is easy to change).

## What's in here

* `p4src`: the code for the switches (data plane)
* `controller`: the code for the network controller (control plane)
* `test`: Integration tests for the various components
* `demo`: runs the controller and a few servers + clients, showcases the load balancing
* `presentation`: slides + assets for the presentation
* `doc`: the report

See the README files inside the directories for information about the specific parts.

## How to run everything in here

### P4 stuff

The `demo/` directory and the various subdirectories under `/test` contain an example `p4app.json` and more documentation.

### Python

#### Global install: No virtualenv

Install the dependencies, then manually source `.env`:
```sh
$ sudo pip2 install attrs twisted pytest pytest-twisted
$ ./fix-pythonpath.sh
$ . .env
$ pytest  # for example
```
#### Virtualenv install

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
