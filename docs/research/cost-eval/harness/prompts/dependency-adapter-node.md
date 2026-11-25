You are writing a small adapter module for a test that is already written. The test checks a JavaScript project (at /work/app: a Node API server in `api/`, a React web app in `frontend/`, a Zepp OS watch app in `watch-zepp/`, with their dependencies installed) through a fixed set of functions, and the adapter gives it those functions for this build. You don't see the test, and you don't decide anything it checks.

The functions the adapter exports, fixed in advance:

<interface>
{INTERFACE}
</interface>

What the adapter may do to provide them, and nothing else:

{OPERATIONS}

The adapter as written for the project before its most recent change:

```js
{DEFAULT}
```

1. See what the most recent change did: `/work/out/change.diff` is its diff, of code and tests. Read the code it touches and the code the functions above reach.
2. If that adapter exports `available = false` (the project before the change had nothing for it to use), it is not one to keep: write the module from the interface wherever this build now provides the functions. Otherwise, if the build still works the way that adapter expects, keep it as it is. If the build provides what a function needs another way (another route, another action, another name), write the function to use that, within the permitted operations. If the build has nothing that provides a function, say so (step 4) rather than providing it yourself.
3. Write the module to `/work/out/adapters/{ID}.js`. It is placed at `/work/app/{DEST}` and imported from there as a namespace, so import the project's modules relative to that path. Export `available` (`true`) and every function in the interface. You may check it with a throwaway test file beside that path, run as the project's own tests run, and delete it afterwards.
4. Record what you did in `/work/out/adapters/{ID}.json`: `{"status": "adapted" | "absent" | "unclear", "evidence": [{"file": "<path>", "symbols": ["<function, route, or action>"]}], "note": "<one sentence>", "notes": {"<key>": "<value>"}}`:
   - adapted: the module provides every function through the build's own code; cite what it uses;
   - absent: the build has nothing that provides one of the functions; cite what you checked;
   - unclear: you can't tell.

   Where the interface asks for a note (how the build stores something, say), give it under `notes`.

Don't write anything else in /work/app, and don't change the project's code.
