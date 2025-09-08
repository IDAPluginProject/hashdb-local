#!/usr/bin/env python
DESCRIPTION = "ROL 7 and negate"
TYPE = 'unsigned_int'
# Test must match the exact has of the string 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
TEST_1 = 2084676916


def hash(data):

    def u32(i):
        return i & 0xFFFFFFFF

    def rol(i, n):
        return u32((i << n) | (i >> (32-n)))

    hash_value = 0

    for c in data:
        hash_value = c ^ rol(hash_value, 7)
        hash_value = (~hash_value+1) & 0xFFFFFFFF

    return hash_value
