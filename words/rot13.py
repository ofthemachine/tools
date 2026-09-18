#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:40a0c59734ba13c96f04853336dd4356ebc3e5981e930ec3f3fa4a7c74ee507e
#: d=ROT13 a string (its own inverse -- run it twice to get the original back). Pure computation, no network.
#: when=Use when the user asks to ROT13 encode or decode text.
#: network=none
#: stdin=none
#: param=text:required:d=Text to encode or decode
import codecs
import os

text = os.environ["TEXT"]
print(codecs.encode(text, "rot_13"))
