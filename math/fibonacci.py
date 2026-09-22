#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
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
