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

import xxhash

DESCRIPTION = "xxhash32 with SEED = 1 and add 0x586A2BE" 
TYPE = 'unsigned_int'
TEST_1 = 0x35b1ff06


def hash(data):
    x = xxhash.xxh32(seed=1)
    x.update(data)
    hex_hash = x.intdigest()
    val = hex_hash + 0x586A2BE
    return val
