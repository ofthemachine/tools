#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
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
