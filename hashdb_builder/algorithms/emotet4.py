#!/usr/bin/env python
DESCRIPTION = "Emotet4 December 2021"
TYPE = 'unsigned_int'
# Test must match the exact has of the string 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
TEST_1 = 4012183583


def hash(data):
    hash_value = 0
    for i in range(len(data)):
        hash_value = ((65599 * hash_value) + i) & 0xFFFFFFFF

    return hash_value
