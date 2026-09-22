#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Search Roku's own on-device universal search for a title and play the Nth result -- Home to a known state, opens Search, types the query, moves into the results row, opens the chosen result, and presses Select up to confirm_selects times to clear a provider-choice screen and/or a profile picker. Built from a live-mapped sequence (Home, Down x6 to Search, type, Right x6 to result 1); result_index beyond 1 extrapolates one more Right per position and is untested. Timing is fixed-delay and can be thrown off by slow app intro animations -- if playback doesn't start, a manual follow-up home-automation/roku-keypress.py -p key=Select is the fix, same as a human would do.
#: when=Use when the user names a show or movie to play on a Roku without saying which app -- e.g. "play Seinfeld" -- and wants Roku's own cross-provider search used to find and start it, rather than a specific app's deep link.
#: network=required
#: stdin=none
#: param=ip:required:d=LAN IP address of the Roku, e.g. 192.168.0.73
#: param=query:required:d=Text to search for, e.g. "stargate atlantis"
#: param=result_index:default=1:d=Which result to open, counting from 1 (left to right in the results row). Only result_index=1 has been verified live; higher values extrapolate.
#: param=confirm_selects:default=1:d=How many times to press Select after opening the result, to clear a provider-choice and/or profile-picker screen. Some apps need a second Select that a slow intro animation can cause to land too early -- if it doesn't stick, send one more home-automation/roku-keypress.py -p key=Select by hand.
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ip = os.environ["IP"]
query = os.environ["QUERY"]
result_index = int(os.environ["RESULT_INDEX"])
confirm_selects = int(os.environ["CONFIRM_SELECTS"])

if result_index < 1:
    print(f"result_index must be >= 1, got {result_index}", file=sys.stderr)
    sys.exit(1)


def ecp_post(path: str) -> None:
    url = f"http://{ip}:8060/{path}"
    req = urllib.request.Request(url, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10):
            pass
    except urllib.error.URLError as e:
        print(f"roku play failed on {path}: {e}", file=sys.stderr)
        sys.exit(1)


def keypress(key: str) -> None:
    ecp_post(f"keypress/{urllib.parse.quote(key)}")


keypress("Home")
time.sleep(3)

for key in ["Down", "Down", "Down", "Down", "Down", "Down", "Select"]:
    keypress(key)
    time.sleep(0.3)
time.sleep(1.2)

for ch in query:
    keypress(f"Lit_{ch}")
    time.sleep(0.15)
time.sleep(1.5)

rights_to_result = 6 + (result_index - 1)
for _ in range(rights_to_result):
    keypress("Right")
    time.sleep(0.3)

keypress("Select")
time.sleep(2.5)

for _ in range(confirm_selects):
    keypress("Select")
    time.sleep(3.5)

print(f'OK: searched "{query}" on {ip}, opened result {result_index}, sent {confirm_selects} confirm Select(s)')
