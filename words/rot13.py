#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=ROT13 a string (its own inverse -- run it twice to get the original back). Pure computation, no network.
#: when=Use when the user asks to ROT13 encode or decode text.
#: network=none
#: stdin=none
#: param=text:required:d=Text to encode or decode
import codecs
import os

text = os.environ["TEXT"]
print(codecs.encode(text, "rot_13"))
