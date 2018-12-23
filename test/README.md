# How to run the tests

We use pytest to run the tests.

1. install pytest: `sudo pip2 install pytest pytest-twisted`
2. run the tests: `pytest`
    * if you installed with pipenv, you need either to run `pytest` inside a `pipenv shell`, or use `pipenv run pytest` instead

If you want to run all the tests, run `pytest` in the `test/` directory; if you just want some, you can give it a path as commandline argument and/or run it from a subdirectory.

Note: Do not run `p4run` manually -- the tests will do it for you.

-----------------------------------------------------------------------

Some tests are occasionally a bit flaky. If things crash or fail, try re-running the same thing. Also, if things are stuck without any progress for more than ~30 seconds, it's probably gotten stuck and it should be restarted.

The causes for the flakiness are AFAIK one of:

* the switch is compiled with debugging, which makes it too slow to not drop packets
* crc32 is not a very good hash function: some tests check for the distribution of requests among several servers, and sometimes we get unlucky and crc32 hashes very non-uniformly. (Currently those tests are disabled.)
* things work when they shouldn't: one test tests that connections break with the simple load balancer, but once in a while we get lucky and it doesn't.
* leftovers from a previous run: Sometimes things can't bind to a socket because of the TCP timeout, or some UNIX socket weirdness happens. It works when tried later.
* `pipenv` race condition (only when using `pipenv`): pipenv likes to open the Pipfile in exclusive mode, so if the test tries to run several Python processes at the same time (such as multiple servers+clients), the open() in pipenv may fail.

# What's in here?

Each subdirectory contains a `p4app.json` and some test cases.

## What do we test?

Each subdirectory maps to a component of the controller:

1. `l2_lazy` tests the L2 parts: switching => with `assignment_strategy: "l2"`
2. `l3_router_lazy` tests the L3 parts: routing => with `assignment_strategy: "l3"`
3. `l4_loadbalacer-unversioned` tests the simple load balancer: without table versioning -- just pool management
4. `l4_loadbalacer` tests the full load balancer with table versioning, and it makes sure that connections don't break when updating the pools

Just like the controller components, the tests build on top of each other: the lower parts must work for the higher ones to work. Therefore, if something breaks, it makes sense to run the tests one by one in this order.

## Fixtures

Pytest is magic: if your test function asks for an argument, pytest will inspect it and do something with it. The `conftest.py` files define that something.

Important fixtures (i.e. magic argument names) that I define:

* `p4run`: runs `p4run` with the `p4app.json` in the current directory. The `p4app.json` must have `touch readyfile` in its `exec_scripts` (see existing; explanation below).
* `controller`: runs `./controller` in the current directory, with the switch name as the first argument.
* `process`: Allows running processes (also on mininet hosts), and kills them after the test finishes.
* `remote_module`: Runs a Python module that provides a [`twisted.spread` "remote control"](https://twistedmatrix.com/documents/current/core/howto/pb-intro.html) in a separate process, binds to the socket, and returns the remote control. Kills the process after the test finishes.

They are defined in `./conftest.py`.

More fixtures can  be implemented in the test file or in a `conftest.py` file. See https://docs.pytest.org/en/latest/fixture.html .

## How do the tests work?

There are two "kinds" of tests: "old-style" and "new-style" tests.

* The "old-style" tests are from the time before I switched to Twisted: these run the controller in a separate process and test using shell commands such as `ping` or `netcat` (run via `mx`).
* The "new-style" tests use `remote_module` and Twisted async awesomeness to provide more fine-grained control and checking: for these, the controller runs inside the test process (so that its internal state can be inspected), and the clients and servers can be finely controlled with a [`twisted.spread` "remote control"](https://twistedmatrix.com/documents/current/core/howto/pb-intro.html).

See `../twisted-intro.md` for a quick intro to Twisted.

### Automatically running `p4run`

I wanted to make pytest run p4run, so that running the tests really is one command and the setup/teardown is managed from within pytest. This has proven to be horrible, because `p4run` does not expect to be used non-interactively. Therefore, workaround:

I use the `exec_scripts` config option in `p4app.json` to create a file. Then I wait for that file to appear within the test, and only proceed once it's there.

The scripts are called when mininet is ready, so the file does not appear too early. This is the only reliable way I found to detect that it's ready. It's not pretty, but it works. Just don't forget to put the thing into `p4app.json`.

The fixture is implemented in `./conftest.py`.
