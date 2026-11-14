You are writing an interface reference for a piece of software. Graders who have never seen it will operate it from outside, using only your reference: they load setup data, make requests, and read the responses. They will not see the source, the docs, or the tests.

The software's repository is at /work/app. Don't change anything in it, except that installing its dependencies there (for example a `.venv`) is fine. Use /tmp for anything else you need to write, including the service's data while you try it.

1. Read the README and enough of the code to find how to start the service, how setup data gets in, and every operation it offers.
2. Start the service yourself on an empty data location under /tmp. Make every call you document once, and copy the real request and response into the reference. Use dates in the future for anything that must not be in the past. Don't wait for time to pass: documenting how calls look never needs it. Stop the service when you're done.
3. Write the reference to /work/out/reference.md, following the template below exactly.
4. Write the start spec to /work/out/start.json, then check it: start the service exactly as the spec says, with `{DATA}` replaced by an empty folder under /tmp, and make one request.

The reference says how to call things, never what they are for or what rules apply. Don't state requirements, business rules, limits, or reasons, and don't quote docs, specs, comments, or test names. Name each operation plainly ("create a booking") and give the exact call. If a real response happens to show a refusal, include it as an example of how refusals look, without explaining why it was refused.

## The start spec

`/work/out/start.json` tells the grading harness how to run the service. It is JSON with these keys:

- `workdir`: the folder to start from, inside /work/app.
- `command`: the exact shell command that starts the service in the foreground, as the README gives it, with its dependencies already installed.
- `env`: environment variables the command needs, as an object (may be empty).
- `port`: the port the service listens on. It must listen on 0.0.0.0 or 127.0.0.1 inside the container.
- `data_path`: the folder or file where the service keeps all its data.
- `ready_path`: a path that answers a GET request once the service is up (for example `/docs`).
- `setup_commands`: the exact commands, if any, that load setup data from the command line, as they would be typed in `workdir`, without their arguments. Leave it empty if setup data goes in through HTTP.

If the service needs a secret, such as an admin token or a first administrator's key, graders must be able to get it without reading the source or the data folder. Prefer a way to set it at start-up (an environment variable or a start-up option): set it in `env` or `command`, and use that same value in every example in the reference, so graders can copy the calls as they are. If the service can only generate it, name the exact command that creates or prints it in `setup_commands`, and show it in the reference. Check, by starting the service from the spec on an empty data folder, that a grader following the reference can load setup data.

Write `{DATA}` wherever the data location goes, in `command`, `env`, or `data_path`, so the harness can point each run at its own empty location. For example: `"env": {"APP_DATA_DIR": "{DATA}"}, "data_path": "{DATA}"`.

## The reference template

{TEMPLATE}
