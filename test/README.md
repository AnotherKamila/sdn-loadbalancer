# How to run the test

We use Python 3 and pytest to run the tests.

Therefore, to run the tests:

1. make sure you have python 3 and pip 3: `sudo apt-get install python3 python3-pip`
2. install pytest: `sudo pip2 install pytest`
3. run the tests: `pytest`
    * if you installed with pipenv, you need either to run `pytest` inside a `pipenv shell`, or use `pipenv run pytest` instead

(Obviously, if you use the VM, you need to run this in the VM.)

If you want to run all the tests, run `pytest` in the `test/` directory; if you just want some, you can give it commandline arguments and/or run it from a subdirectory.

Note: Do not run `p4run` manually -- the tests will do it for you if you ask for an argument called `p4run` (see existing).

# How do the tests work?

Each subdirectory contains a `p4app.json` and some test cases.

At the beginning of each file, we create a fixture that runs `p4run` with the `p4app.json` in the current directory. Therefore, each file is a collection of related test cases that can (and will) be run in the same p4run session.

Then it is plain `pytest` that runs shell commands inside the hosts using `mx` and looks at the exit status. (This is horrible. And it works.)

See the existing stuff for examples.

Make sure to copy the `exec_scripts` section of `p4app.json` from the existing stuff when creating a new config. (Wondering why? Read on...)

If you need fixtures, you can implement them in the file or in a `conftest.py` file. See https://docs.pytest.org/en/latest/fixture.html .

## Horrible hack

I wanted to make pytest run p4run, so that running the tests really is one command and the setup/teardown is managed from within pytest. This has proven to be horrible, because `p4run` is not expecting to be used non-interactively. Therefore, workaround:

I use the `exec_scripts` config option in `p4app.json` to create a file. Then I wait for that file to appear within the test, and only proceed once it's there.

The scripts are called when mininet is ready, so the file does not appear too early. This is the only reliable way I found to detect that it's ready. Everything is terrible. But it works. Just don't forget to put the thing into `p4app.json`.

The horribleness is implemented in `./conftest.py`. Abandon all hope, ye who enter here.

# Trick for debugging (not only for tests!)

Best thing ever:

```python
# put this in there instead of that printf
from ptpython.repl import embed
embed(globals(), locals())  # has access to all the variables
```
