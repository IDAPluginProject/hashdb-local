#!/usr/bin/env python

DESCRIPTION = """
Modified ROR13 add algo used in the Lockbit 3.0 with a seed of 0x0 
and a hard coded hash start of 0xC8B32494

Reference: https://c3rb3ru5d3d53c.github.io/malware-blog/lockbit-v3-api-hashing/
"""
TYPE = 'unsigned_int'
EXTENDED_PERMUTATION = True
TEST_1 = 2949122496 #1345844799 
TEST_API_DATA_1 = b'kernel32.dll,FindFirstFileExW'
TEST_API_1 = 0xaae0cefb ^ 0x29009fe6 # 2212516125 =='0x83e0511d'

ROTATE_BITMASK = {
    8: 0xff,
    16: 0xffff,
    32: 0xffffffff,
    64: 0xffffffffffffffff,
}

def ror(inVal, numShifts, dataSize=32):
    '''rotate right instruction emulation'''
    if numShifts == 0:
        return inVal
    if (numShifts < 0) or (numShifts > dataSize):
        raise ValueError('Bad numShifts')
    if (dataSize != 8) and (dataSize != 16) and (dataSize != 32) and (dataSize != 64):
        raise ValueError('Bad dataSize')
    bitMask = ROTATE_BITMASK[dataSize]
    return bitMask & ((inVal >> numShifts) | (inVal << (dataSize-numShifts)))


def hash_algo(string, seed):
    s = string + b'\0'
    result = seed ^ 0xC8B32494
    for c in s:
        result = ror(result, numShifts=0x0d, dataSize=32)
        result = (result + c)
        if c == 0x00:
            break
    return result


def hash(data):
    hash_dll = 0
    seed = 0
    final_hash = 0
    splitted_data = data.split(b",")
    if len(splitted_data) > 1:
        hash_dll = hash_algo(splitted_data[0], seed)
        hash_api_with_dll_seed = hash_algo(splitted_data[1], hash_dll)
        final_hash = hash_api_with_dll_seed
    else:
        final_hash = hash_algo(data, seed)

    return ~final_hash & 0xffffffff
