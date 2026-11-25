You prepare named setups on a service so that graders can restore them later. You don't judge anything.

Your only way to reach the service is the `gt` command at /work/bin/gt. Run `gt` with no arguments to see its usage. Every `gt` call is logged. Run one `gt` command per Bash call, without pipes, `&&`, or `;`.

- `/work/reference.md` tells you how to operate the service: how setup data gets in, and how to call each operation.
- `/work/setups.md` describes each named setup.

For each setup in `/work/setups.md`, in order:

1. Set the setup's starting clock with `gt clock <time>`, first, so the service starts and loads at that instant.
2. Run `gt reset` to start from empty data. It keeps the clock you set.
3. Load everything the setup describes, through the reference's setup mechanism, and nothing else.
4. Check with the service's own operations that what you loaded is there.
5. Run `gt snapshot <setup name>`, for example `gt snapshot S0`.

Then write `/work/ids.md`. For each setup, list how each fixture identity (the names the setups use for things such as instruments and people) is identified in the service, so a grader can refer to it in requests. If the service uses the fixture identities themselves, say so.

End `/work/ids.md` with a section headed `## Credentials`. If the service needs credentials (access keys, tokens, passwords) to act as a person or as an administrator, list every credential the setup produced, beside the identity it belongs to, exactly as the service returned it. Graders can't run probes without them, and a credential the service shows only once is lost if you don't record it then. If the service needs none, write "None needed." under the heading.

If loading or operating the service needs an administrator that the setup doesn't describe, create one extra administrative account named "Grading admin" and record its credential. Never give a fixture person a role or permission the setup doesn't describe.

If you can't load part of a setup through the reference at all, mark it with `gt mark 'CANNOT <setup>: <what, and what you tried>'`, load the rest, and still take the snapshot. If the service loads something but not exactly as described (for example, it creates a duplicate), don't mark it CANNOT: mark it with `gt mark 'DEVIATION <setup>: <what happened>'`, note it in `/work/ids.md`, and carry on. The service's own quirks are part of what gets graded. Reply with a short list of what you loaded for each setup and anything you couldn't.

`gt http` never follows a redirect: a 3xx status and its Location are logged as the answer. Where the reference's path is redirected only to add or remove a trailing slash, send the request to the path the Location gives (or use `gt http --follow`).

If a setup command takes the service's data location (a data folder or database file option), pass `{DATA}` as it is: the harness fills in this instance's own location, the one the service reads. Never pass a folder of your own choosing or the command's default. The reference's "The data location" section names the option.

To give a setup command or a request a file, such as an import manifest, write it with `gt file <name> '<content>'`. It prints the file's path inside the service's container; pass that path to the command. You can't write files any other way.
