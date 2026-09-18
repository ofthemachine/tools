#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:40a0c59734ba13c96f04853336dd4356ebc3e5981e930ec3f3fa4a7c74ee507e
#: d=The Nth Fibonacci number (0-indexed: F(0)=0, F(1)=1). Pure computation, no network.
#: when=Use when the user asks for a Fibonacci number by index.
#: network=none
#: stdin=none
#: param=n:required:d=0-indexed position of the Fibonacci number to compute
import os

n = int(os.environ["N"])
if n < 0:
    raise SystemExit("n must be non-negative")
a, b = 0, 1
for _ in range(n):
    a, b = b, a + b
print(f"Value: {a}")
