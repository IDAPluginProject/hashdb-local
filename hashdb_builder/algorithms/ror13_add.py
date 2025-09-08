#!/usr/bin/env python
########################################################################
# Copyright 2012 Mandiant
# Copyright 2014 FireEye
#
# Mandiant licenses this file to you under the Apache License, Version
# 2.0 (the "License"); you may not use this file except in compliance with the
# License. You may obtain a copy of the License at:
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied. See the License for the specific language governing
# permissions and limitations under the License.
#
# Reference:
# https://github.com/mandiant/flare-ida/blob/master/shellcode_hashes/make_sc_hash_db.py
#
########################################################################

DESCRIPTION = "ROR 13 dll (unicode) ADD ROR 13 api"
EXTENDED_PERMUTATION = True
TYPE = 'unsigned_int'
TEST_1 = 2879724916
TEST_API_DATA_1 = 'ntdll.dll,RtlFreeHeap' #0xfed0806a
TEST_API_1 = 0xbdba08b3 + 0x95c006d0

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

def get_hash(input_string):
    hash_value = 0
    for byte in input_string:
        rotated = ror(hash_value, 0xd, 32)
        hash_value = byte + rotated  
    return hash_value

def hash(raw_data):
    hash_dll = 0
    hash_api = 0
    final_hash = 0
    splitted_data = raw_data.split(b",")
    if len(splitted_data) > 1:
        hash_dll = get_hash(splitted_data[0] + b'\x00\x00')
        hash_api = get_hash(splitted_data[1] + b'\0')
        final_hash = hash_dll + hash_api
    else:
        final_hash = get_hash(raw_data)

    return final_hash
