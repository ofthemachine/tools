#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Check whether a number is prime, and show its smallest prime factor if not. Pure computation, no network.
#: when=Use when the user asks whether a number is prime or for its smallest factor.
#: network=none
#: stdin=none
#: param=n:required:d=Integer to test for primality
import os

n = int(os.environ["N"])
if n < 2:
    print("Prime: no")
    print("Reason: less than 2")
    raise SystemExit(0)

factor = None
i = 2
while i * i <= n:
    if n % i == 0:
        factor = i
        break
    i += 1

if factor:
    print("Prime: no")
    print(f"Smallest Factor: {factor}")
else:
    print("Prime: yes")
