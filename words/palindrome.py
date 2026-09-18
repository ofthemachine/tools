#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:40a0c59734ba13c96f04853336dd4356ebc3e5981e930ec3f3fa4a7c74ee507e
#: d=Check whether text is a palindrome, ignoring case, spaces, and punctuation. Pure computation, no network.
#: when=Use when the user asks whether a word or phrase is a palindrome.
#: network=none
#: stdin=none
#: param=text:required:d=Text to check
import os
import re

text = os.environ["TEXT"]
cleaned = re.sub(r"[^a-z0-9]", "", text.lower())
is_pal = len(cleaned) > 0 and cleaned == cleaned[::-1]
print(f"Palindrome: {'yes' if is_pal else 'no'}")
print(f"Cleaned: {cleaned}")
