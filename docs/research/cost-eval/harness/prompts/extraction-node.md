You are writing an interface reference for a JavaScript project: a self-hosted gym app in one repository, with a Node API server (`api/`), a React web app (`frontend/`), a Zepp OS watch app (`watch-zepp/`) and an MCP bridge (`mcp/`). Graders who have never seen it will write tests against it using only your reference: they build the state a scenario needs, drive the project through its own code, and print what they observe. They will not see the source, the docs, or the existing tests.

The project is at /work/app, with its dependencies installed. Don't change anything in it, except throwaway test files while you check your examples (step 3).

1. See what the most recent change did: `/work/out/arm.diff` is its diff, of code and tests. Read the code it touches, and enough around it to use it.
2. Work out how a test reaches it, in each part the graders will test, as their tests will run:

{PACKAGES}

   Cover the functions, components, routes and modules the change added or altered, and the basic calls for building state and reading it back. For the API: how to start `server.js` as a child process on a data folder of its own and the port it binds, how to sign in or get a session and any proof a route asks for, and how to call its routes. For the web app: how to render a view or component into happy-dom, drive it (clicks, typing, timers) and read what it shows, and how its store is set and read, persisted and reloaded. For the watch: how to load a page against the stand-ins for the Zepp OS modules, press its buttons, move its clock, and read what it queued. Name the existing test helpers that do any of this, with their exact import paths.
3. Check every example you document: put them in a throwaway test file in the folder named above for that part, `zz_reference_check.test.js` (`.test.jsx` for the web app), run it as given there, fix the reference until the examples run, then delete the file.
4. Write the reference to /work/out/reference.md: for each operation, its name in plain words, the exact code to do it (the imports and a short example that runs), and what it returns, with a real value printed from your check where it helps.

{ITEMS}The reference says how to call things, never what they are for or what rules apply. Don't state requirements, rules, limits, or reasons, and don't quote docs, specs, comments, or test names. If a call you checked happened to return an error or refuse something, you may show it as an example of how refusals look, without saying why.
