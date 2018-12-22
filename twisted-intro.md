# Twisted intro

Twisted is an asynchronous framework: it runs the event loop and calls our code when something interesting happens. (Unlike other frameworks, you don't call Twisted, Twisted calls you.)

Twisted is quite similar to Python 3's `async/await` (and was in fact the inspiration for these). It just has a bit weirder syntax because it's Python 2-compatible.

Things to know:

* a `Deferred` is Twisted's name for promises/futures: it is an unfinished
  computation that fires and calls its callbacks when done.
* We could manually create `Deferred`s and add callbacks, but that would lead to
  code that is hard to follow and possibly disappears off the right edge of the
  screen (known as callback hell). To avoid that, Twisted provides a
  `@defer.inlineCallbacks` decorator. This decorator provides functionality
  equivalent to Python 3's `await` keyword in Python 2: with it, we can type
  `yield` in front of `Deferred`s and our code will pause (and something else
  will execute) until that `Deferred` fires. When it fires, our code will resume
  execution. A `yield` with `@inlineCallbacks` can be pronounced `await`,
  because that's what it is.
  
  We can type `yield something` to just wait, or `x = yield something` to also
  get the result of the computation.

  If we `yield` (i.e. await) something and an error happens, an exception will
  be raised, and exceptions propagate nicely across the async code.
* Twisted does not have an explicit marker for async functions: we need to keep in mind when functions return `Deferred`s.
* We normally do not need to worry about thread-safety/locking: only one thread at a time will be running (unless we create threads ourselves). We do need to worry about order of operations, because it's asynchronous. When we need an operation to have finished before we continue, we should `yield` on it (or add a callback).
