#!/usr/bin/env python

DESCRIPTION = "Custom hashing algorithm by adding ordinal value of chars."
TYPE = 'unsigned_int'
TEST_1 = 5387


def hash(data):
    hash_sum = sum([byte for byte in data])
    return 0xffffffff & hash_sum
