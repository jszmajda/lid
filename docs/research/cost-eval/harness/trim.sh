#!/bin/sh
# Return released Docker space to macOS: trim the VM's filesystems. Colima's disk image only shrinks once trimmed, so
# removed volumes otherwise keep their space on the Mac. It takes seconds and never fails its caller. TRIM_CMD, a
# script, stands in for it in tests.
if [ -n "$TRIM_CMD" ]; then
  sh "$TRIM_CMD"
else
  docker run --rm --privileged --pid=host alpine nsenter -t 1 -m -u -n -i fstrim -av > /dev/null 2>&1
fi
exit 0
