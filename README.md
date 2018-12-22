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

### Python

I use `pipenv` to manage the dependencies. Assuming you have `pip2`, install `pipenv` using:

```sh
sudo pip2 install pipenv
```

Then run everything inside a `pipenv shell` to get the virtualenv. Assuming this repository is at `/project`:

```sh
$ cd /project
$ pipenv shell
# pipenv will install dependencies
# now you can run things inside the venv
```

### P4 switch

The `demo/` directory and the various subdirectories under `/test` contain an example `p4app.json` and more documentation.
