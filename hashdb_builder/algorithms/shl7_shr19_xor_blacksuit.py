#!/usr/bin/env python

DESCRIPTION = "API hashing used by BlackSuit"
TYPE = 'unsigned_long'
TEST_1 = 0x7263b4dd3941  # hash(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")


def hash(data):
    def cast32(i):
        return i & 0xFFFFFFFF

    if len(data) == 0:
        return -1

    hash64 = 0x659EB25FF8A6C6FC

    for i in data:
        hash64 = i ^ ((hash64 >> 25) | ((hash64 & 0x1FFFFFF) << 7))

    # Result is an 48-bit value including the first and last character for collision reduction.
    val = data[0] | (data[-1] << 8) | (cast32(hash64) << 16)

    return val
