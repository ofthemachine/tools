#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:40a0c59734ba13c96f04853336dd4356ebc3e5981e930ec3f3fa4a7c74ee507e
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
