#!/usr/bin/env python3

"""
Copyright (c) 2026 G DATA Advanced Analytics GmbH

This file is licensed under the BSD 3-Clause License.
See the LICENSE-BSD3 file in the project root for full license information.
"""

import sqlite3
import algorithms
from sqlite3.dbapi2 import Connection
from typing import List, Tuple
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STRINGS_FILE = os.path.join(SCRIPT_DIR, "strings.txt")
IMPORT_DB = os.path.join(SCRIPT_DIR, "functions_with_forwards.sqlite3")
HASH_DB = os.path.join(SCRIPT_DIR, "db/tools/hashdb.sqlite3")
VALUE_TYPES = ('null', 'module', 'api', 'dll', 'string')
TRANSFORM_TYPES = ('lower', 'upper', 'unicode')
PERMUTATIONS = ["api", "api_lower", "api_upper", 
                "dll", "dll_lower", "dll_upper",
                "module", "module_lower", "module_upper",
                "string", "string_lower", "string_upper"]
EXTENDED_PERMUTATIONS = ["dll_lower_api", "dll_upper_unicode_api"]


class AlgorithmError(Exception):
    pass


def db_connect_import_db() -> Connection:
    return sqlite3.connect(IMPORT_DB)


def db_connect_hash_db() -> Connection:
    os.makedirs(os.path.dirname(HASH_DB), exist_ok=True)
    return sqlite3.connect(HASH_DB)


def setup_db(hash_db: Connection):

    try:
        con = hash_db.cursor()
        con.execute(
            "CREATE TABLE IF NOT EXISTS modules " +
            "(id integer PRIMARY KEY AUTOINCREMENT, module varchar UNIQUE)")

        con.execute(
            "CREATE TABLE IF NOT EXISTS strings " +
            "(id integer PRIMARY KEY AUTOINCREMENT, string varchar UNIQUE, is_api Boolean)")

        con.execute(
            "CREATE TABLE IF NOT EXISTS strings_modules_mapping " +
            "(id integer PRIMARY KEY AUTOINCREMENT, string_id integer, module_id integer, " +
            "FOREIGN KEY(string_id) REFERENCES strings(id), " +
            "FOREIGN KEY(module_id) REFERENCES modules(id), " +
            "UNIQUE(string_id, module_id))")

        con.execute(
            "CREATE TABLE IF NOT EXISTS algorithms " +
            "(id integer PRIMARY KEY AUTOINCREMENT, algorithm varchar UNIQUE, " +
            "extended_permutation boolean, description text, type varchar)")

        con.execute(
            "CREATE TABLE IF NOT EXISTS permutations " +
            "(id integer PRIMARY KEY AUTOINCREMENT, permutation text UNIQUE)")

        con.execute(
            "CREATE TABLE IF NOT EXISTS hashes " +
            "(id integer PRIMARY KEY AUTOINCREMENT, hash integer, algorithm_id integer, " +
            "string_id integer, permutation_id integer, " +
            "UNIQUE(hash, algorithm_id, string_id, permutation_id), " +
            "UNIQUE(hash, algorithm_id, string_id), " +
            "FOREIGN KEY(algorithm_id) REFERENCES algorithms(id), " +
            "FOREIGN KEY(string_id) REFERENCES strings(id), " +
            "FOREIGN KEY(permutation_id) REFERENCES permutations(id))")

        hash_db.commit()
        con.close()
    except sqlite3.Error as error:
        print("Failed to setup the database", error)
    finally:
        con.close()


def list_algorithms():
    return list(algorithms.modules.keys())


def hash(algorithm_name, data):
    if algorithm_name not in list(algorithms.modules.keys()):
        raise AlgorithmError("Algorithm not found")
    if type(data) == str:
        data = data.encode('utf-8')
    return algorithms.modules[algorithm_name].hash(data)


def insert_algorithms(hash_db: Connection):
    '''
    Fills the algorithms table with the content from algorithm folder
    Inserts each algorithm into algorithms table which are in algorithm folder
    '''
    algos = list_algorithms()
    params = []
    for algo in algos:
        
        desc = algorithms.modules[algo].DESCRIPTION
        type = algorithms.modules[algo].TYPE
        try:
            ext_permu = algorithms.modules[algo].EXTENDED_PERMUTATION
        except AttributeError:
            ext_permu = False
            
        params.append((algo, ext_permu, desc, type))
    try:
        con = hash_db.cursor()
        con.executemany("INSERT or IGNORE INTO algorithms(algorithm, extended_permutation, description, type) " +
                        "VALUES(?, ?, ?, ? )", params)
        hash_db.commit()
    except sqlite3.Error as error:
        print("insert_algorithms: ", params, error)
    finally:
        con.close()


def insert_permutations(hash_db: Connection):
    '''
    Fills the permutations table
    '''
    try:
        con = hash_db.cursor()
        con.executemany(
            "INSERT or IGNORE INTO permutations(permutation) VALUES(?)", ((name, ) for name in (PERMUTATIONS + EXTENDED_PERMUTATIONS)))
        hash_db.commit()
    except sqlite3.Error as error:
        print("insert_permutations: ", error)
    finally:
        con.close()


def import_dll_in_modules(hash_db: Connection, import_db: Connection):
    '''
    Fills the modules table.
    It use the database (functions_with_forwards.sqlite3) with exported names.
    Imports the values from the dll column in functions table into modules table
    of the new created table.
    '''
    try:
        con = hash_db.cursor()
        import_con = import_db.cursor()

        # collect all modules from the import_db
        import_con.execute("SELECT dll from functions where dll is not null group by dll", ())
        modules = import_con.fetchall()
        # insert collected modules in new db
        con.executemany(
            "INSERT or IGNORE INTO modules (module) VALUES(?)", modules)
        hash_db.commit()

    except sqlite3.Error as error:
        print("import_dll_in_modules: ", error)
    finally:
        con.close()
        import_con.close()


def import_functions_in_strings(hash_db: Connection, import_db: Connection):
    '''
    Import the functions into strings table
    '''
    try:
        con = hash_db.cursor()
        import_con = import_db.cursor()

        import_con.execute(
            "SELECT name from functions WHERE name is not null")
        functions = import_con.fetchall()

        func_params = []
        for name in functions:
            func_params.append((name[0], 1))

        # insert collected functions in new db
        con.executemany("INSERT or IGNORE INTO strings (string, is_api) VALUES(?, ?)", func_params)
        hash_db.commit()

    except sqlite3.Error as error:
        print("import_functions_in_strings: ", error)
    finally:
        import_con.close()
        con.close()


def import_strings_modules_mapping(hash_db: Connection, import_db: Connection):
    '''
    Import the dependencies between apis and modules
    '''
    try:

        con = hash_db.cursor()
        import_con = import_db.cursor()

        # collect all functions with dll from import db
        import_con.execute(
            "SELECT name, dll from functions WHERE name is not null")
        apis = import_con.fetchall()

        # prepare params for query
        params = []
        for api_name, module_name in apis:
            params.append((api_name, module_name))

        # insert dependencies between strings (apis)
        # and modules into strings_modules_mapping
        con.executemany("INSERT or IGNORE INTO strings_modules_mapping (string_id, module_id) " +
                        "VALUES(" +
                        "(SELECT id from strings where strings.string =?), " +
                        "(SELECT id from modules where modules.module =?))", params)
        con.fetchall()
        hash_db.commit()

    except sqlite3.Error as error:
        print("import_strings_modules_mapping: ", error)
    finally:
        import_con.close()
        con.close()


def import_dlls_in_strings(hash_db: Connection, import_db: Connection):
    '''
    Import the dlls (modules) from the old db into strings (new db)
    '''
    try:

        con = hash_db.cursor()
        import_con = import_db.cursor()

        # collect all dll from import db
        import_con.execute(
            "SELECT dll from functions WHERE dll is not null")
        dlls = import_con.fetchall()

        modules_params = []
        for dll in dlls:
            modules_params.append((dll[0], 0))

        # insert collected dlls in new db as string
        con.executemany(
            "INSERT or IGNORE INTO strings (string, is_api) VALUES(?, ?)", modules_params)
        hash_db.commit()

    except sqlite3.Error as error:
        print("import_dlls_in_strings: ", error)
    finally:
        import_con.close()
        con.close()


def import_strings_from_file(hash_db: Connection):
    '''
    Import the strings from strings.txt into strings table
    '''
    try:
        con = hash_db.cursor()
        string_params = []

        # prepare params from strings.txt for query
        with open(STRINGS_FILE) as file:
            for line in file:
                string_params.append((line.rstrip(), 0))

        # insert strings from strings.txt
        con.executemany(
            "INSERT or IGNORE INTO strings (string, is_api) VALUES(?, ?)", string_params)
        hash_db.commit()

    except sqlite3.Error as error:
        print("import_strings_from_file: ", error)
    finally:
        con.close()


def generate_hashes(hash_db: Connection):
    '''
    Generates hashes with each algorithm, each permutation for each row in strings table.
    '''
    try:
        con = hash_db.cursor()

        con.execute("SELECT * from permutations", ())
        permutations = con.fetchall()

        con.execute("SELECT id, algorithm, extended_permutation from algorithms", ())
        algorithms = con.fetchall()

        con.execute("SELECT * from strings", ())
        strings = con.fetchall()

        strings_with_modules = []
        for string_id, string, is_api in strings:
            if is_api:
                con.execute(
                    "SELECT module from strings_modules_mapping as smm " +
                    "inner join modules on modules.id = smm.module_id " +
                    "where string_id = ?", (string_id,))
                modules_from_string = con.fetchall()
            else:
                modules_from_string = None

            strings_with_modules.append((string_id, string, is_api, modules_from_string))

        # start generate hashes with each algorithm
        print("#### Start generating hashes for the whole db ####")
        for algorithm_id, algorithm_name, use_extended_permutation in algorithms:
            print("### Start hashing with algorithm ###")
            print(algorithm_name)
            params = []
            permutated_strings = set()

            # and each permutation
            for permutation_id, permutation_name in permutations:

                # and each string
                for string_id, string_value, is_api, modules_from_string in strings_with_modules:
                    def add_it(permutated_string):
                        if permutated_string not in permutated_strings:
                            permutated_strings.add(permutated_string)
                            hash = generate_signed_hash(algorithm_name, permutated_string)
                            params.append((hash, algorithm_id, string_id, permutation_id))

                    if not use_extended_permutation and permutation_name in EXTENDED_PERMUTATIONS:
                        continue

                    if is_api and ("api" in permutation_name):
                        for module_name, in modules_from_string:
                            add_it(generate_permutation(permutation_name, api=string_value, module=module_name))  # noqa:E501
                    elif (not is_api) and ("api" not in permutation_name):
                        add_it(generate_permutation(permutation_name, module=string_value, string=string_value))  # noqa:E501

            con.executemany(
                "INSERT or IGNORE INTO hashes(hash, algorithm_id, string_id, permutation_id) " +
                "VALUES(?, ?, ?, ?)", (params))
            con.fetchmany()
            hash_db.commit()
        print("#### Finish generating hashes ####")

    except sqlite3.Error as error:
        print("generate_hashes: ", error)
    finally:
        con.close()


def generate_signed_hash(algorithm_name, s):
    h = hash(algorithm_name, s)
    return to_signed64(h)


def generate_permutation(permutation, **kwargs):
    """Splits up the permutation description into its single components
       (values like 'api', 'string' and transforms like 'lower') and uses
       them to generate a final string from the values in kwargs."""
    keywords = permutation.split('_')
    result = []
    composition: List[Tuple[str, List[str]]] = []
    i = 0

    while i < len(keywords):
        value_type = keywords[i]
        transform_type = []
        i += 1
        # prepare composition
        while i < len(keywords) and keywords[i] in TRANSFORM_TYPES:
            transform_type.append(keywords[i])
            i += 1
        composition.append((value_type, transform_type))

    # generate permutation with prepared composition
    for value_type, transform_types in composition:
        value = get_value_by_type(value_type, **kwargs)
        for transform_type in transform_types:
            value = transform_value(value, transform_type)

        result.append(value)
    final_result = ",".join(result)

    return final_result


def get_value_by_type(value_type, **kwargs):

    if value_type == 'null':
        return '\x00'
    if value_type == 'api':
        return kwargs.get("api")
    if value_type == 'dll':
        return kwargs.get("module")
    if value_type == 'module':
        return kwargs.get("module")[:-4] if kwargs.get("module").endswith('.dll') else kwargs.get("module")  # noqa:E501
    if value_type == 'string':
        return kwargs.get("string")

    raise AssertionError('unknown value_type: ' + value_type)


def transform_value(string: str, transform_type):
    if transform_type == 'lower':
        return string.lower()
    if transform_type == 'upper':
        return string.upper()
    if transform_type == 'unicode':
        return string.encode('utf-16le').decode('ascii')

    raise AssertionError('unknown transform_type: ' + transform_type)


def to_signed64(n):
    return n | (-(n & 0x8000000000000000))


def from_signed64(n):
    return n & 0xffffffffffffffff


def main():

    hash_db = db_connect_hash_db()
    import_db = db_connect_import_db()

    # 1. create new database with tables
    setup_db(hash_db)
    # 2. insert algorithms into db from algorithms/
    insert_algorithms(hash_db)
    # 3. insert permutations into db
    insert_permutations(hash_db)
    # 4. import dll values from the old db into the new modules table
    import_dll_in_modules(hash_db, import_db)
    # 5. import function values from the old db into the new strings table
    import_functions_in_strings(hash_db, import_db)
    # 6. import the dependencies between functions and dlls into strings_modules_mapping
    import_strings_modules_mapping(hash_db, import_db)
    # 7. import dll values new strings table
    import_dlls_in_strings(hash_db, import_db)
    # 8. import strings from strings.txt into strings table
    import_strings_from_file(hash_db)
    # 9. generate with all algorithms and permutations all hashes for the strings table
    generate_hashes(hash_db)

    hash_db.close()
    import_db.close()


if __name__ == "__main__":

    main()
