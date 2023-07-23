import sys

if len(sys.argv) == 2:
    cipher = b""
    clear = sys.argv[1].encode()
    for c in clear:
        cipher += bytes([c ^ 0x41])
    print(cipher)
