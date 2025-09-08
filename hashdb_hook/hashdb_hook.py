#!/usr/bin/env python3

import json
import os
import sqlite3
import threading
from typing import List, Tuple
from urllib.parse import urlparse
from requests import Timeout, exceptions   # noqa:F401
from requests.models import Response

PATH = os.path.join(os.getenv("LOCALAPPDATA"), "hashdb", "hashdb.sqlite3")
VALUE_TYPES = ('null', 'module', 'api', 'dll', 'string')
TRANSFORM_TYPES = ('lower', 'upper', 'unicode')


class LOCAL_HashDB_Error(Exception):

    def __init__(self, error, param, query):
        m = f"Database Error: {str(error)}\nParams: {param}\nIn Query: {query}"
        super().__init__(m)

class LOCAL_HashDB():

    def __init__(self):
        self._db = threading.local()

    @property
    def db(self):
        if getattr(self._db, "val", None) is None:
            self._db.val = sqlite3.connect(PATH)
        return self._db.val

    def execute_insert_query(self, query, param):
        try:
            con = self.db.cursor()
            con.execute(query, param)
            self.db.commit()
        except sqlite3.Error as error:
            raise LOCAL_HashDB_Error(error, param, query)
        finally:
            con.close()

    def execute_select_query(self, query, param):

        result = []
        try:
            con = self.db.cursor()
            if param is None:
                con.execute(query)
            else:
                con.execute(query, param)

            result = con.fetchall()
            self.db.commit()
        except sqlite3.Error as error:
            raise LOCAL_HashDB_Error(error, param, query)
        finally:
            con.close()

        return result

    def get_algorithms(self):

        return self.execute_select_query(
            "SELECT algorithm, description, type FROM algorithms", None)

    def get_strings_by_hash_and_algorithm(self, algorithm, hash_value):

        return self.execute_select_query(
            "SELECT hash, s.string, s.is_api, p.permutation FROM hashes " +
            "INNER JOIN strings AS s ON s.id = hashes.string_id " +
            "INNER JOIN permutations AS p ON p.id = hashes.permutation_id " +
            "INNER JOIN algorithms AS a ON a.id = hashes.algorithm_id " +
            "WHERE algorithm=? AND hash=?", (algorithm, hash_value))

    def get_hashes_by_module_algorithm_permutation(self, module, algorithm, permutation):

        return self.execute_select_query(
            "SELECT hash, s.string, s.is_api, p.permutation, m.module FROM hashes " +
            "INNER JOIN strings AS s ON s.id = hashes.string_id " +
            "INNER JOIN permutations AS p ON p.id = hashes.permutation_id " +
            "INNER JOIN algorithms AS a ON a.id = hashes.algorithm_id " +
            "INNER JOIN strings_modules_mapping AS smm ON smm.string_id = s.id " +
            "INNER JOIN modules AS m ON m.id = smm.module_id " +
            "WHERE module=? AND algorithm=? AND permutation=?", (module, algorithm, permutation))

    def get_module_as_list_from_string(self, string):

        try:
            con = self.db.cursor()
            con.row_factory = lambda cursor, row: row[0]
            con.execute("SELECT module FROM strings_modules_mapping as smm " +
                        "INNER JOIN modules AS m ON m.id = smm.module_id WHERE string_id = " +
                        "(SELECT id FROM strings WHERE string = ?)", (string,))
            rows = con.fetchall()
            self.db.commit()
            con.close()
        except sqlite3.Error as error:
            raise LOCAL_HashDB_Error(error, string, "get_modules_as_list_from_string")
        finally:
            con.close()
        return rows

    def get_matched_algorithms(self, hashes):

        return self.execute_select_query(
            "SELECT Count(hash) AS count, algorithm FROM hashes " +
            "INNER JOIN algorithms AS a ON a.id = hashes.algorithm_id " +
            "WHERE hash IN (%s)" % ("?," * len(hashes))[:-1], hashes)


# ########################################################
# ########## Request METHODS #############################
# #######################################################

db = LOCAL_HashDB()


def get(api_url, **kwargs) -> Response:

    path, parsed_params = filter_params_from_url(api_url)
    if path == 'hash' and len(parsed_params) == 0:
        return get_algorithms()
    if path == 'hash' and len(parsed_params) > 0:
        return get_strings_from_hash(parsed_params[0], int(parsed_params[1]))
    if path == 'module' and len(parsed_params) > 0:
        return get_module_hashes(parsed_params[0], parsed_params[1], parsed_params[2])

    return build_response(500, [])


def post(api_url, json, **kwargs) -> Response:

    path, parsed_params = filter_params_from_url(api_url)
    hashes = json['hashes']
    if path == 'hunt' and len(parsed_params) == 0:
        return hunt_hash(hashes)
    return build_response(500, [])


def get_algorithms() -> Response:

    algorithms = {}
    algorithm = {}
    l_algo = []
    results = db.get_algorithms()
    if results:
        for algorithm_name, description, type in results:
            algorithm = {'algorithm': algorithm_name,
                         'description': description, 'type': type}
            l_algo.append(algorithm)
            algorithms["algorithms"] = l_algo

    return build_response(200, algorithms)


def get_strings_from_hash(algorithm: str, hash_value: int) -> Response:

    result_hashes = {}
    hashes = []
    hash_value = to_signed64(int(hash_value))
    results = db.get_strings_by_hash_and_algorithm(algorithm, hash_value)
    if results:
        for hash_value, string, is_api, permutation in results:
            hash_element = build_hash_element(hash_value, string, is_api, permutation, None)
            hashes.append(hash_element)
            result_hashes["hashes"] = hashes

    return build_response(200, result_hashes)


def get_module_hashes(module_name: str, algorithm: str, permutation: str) -> Response:

    result_hashes = {}
    hashes = []
    results = db.get_hashes_by_module_algorithm_permutation(
        module_name, algorithm, permutation)
    if results is not []:
        for hash_value, string, is_api, permutation, module in results:
            hash_element = build_hash_element(hash_value, string, is_api, permutation, module)
            hashes.append(hash_element)
            result_hashes["hashes"] = hashes

    return build_response(200, result_hashes)


def hunt_hash(hashes: list) -> Response:

    hits = {}
    l_hits = []
    hashes = [from_signed64(hash) for hash in hashes]

    results = db.get_matched_algorithms(hashes)
    if results is not []:
        for count, algorithm in results:
            hit_element = build_hit_element(count, algorithm)
            l_hits.append(hit_element)
            hits['hits'] = l_hits

    return build_response(200, hits)


# ########################################################
# ########## HELPING METHODS #############################
# #######################################################

def filter_params_from_url(url: str) -> Tuple[str, List[str]]:
    """
    parse url and returns the path and the parameters
    """

    u = urlparse(url)
    path = u.path
    parsed_params = path.rsplit('/')
    parsed_params.remove('')
    parsed_params.reverse()
    root = parsed_params.pop()
    parsed_params.reverse()
    return root, parsed_params


def build_response(code, result) -> Response:
    """
    Build response with code 200, 400 or 400. Response 200 contains contant.
    """

    res = Response()
    res.encoding = 'utf-8'
    if code == 400:
        res.status_code = code
        return res
    if code == 200:
        res.status_code = code
        res.ok
        res._content = json.dumps(result).encode()
    if code == 500:
        res.status_code = code

    return res


def build_hash_element(hash_value, raw_string, is_api, permutation, m):
    """
    Build hash element (json) as needed and append module list for that hash element
    """
    elements = {}
    string = {}
    hash = {'hash': from_signed64(hash_value)}
        # append all modules which contains the same api endpoint
    if is_api:
        modules = db.get_module_as_list_from_string(raw_string)
        for module in modules:
            elements = build_child_hash_element(raw_string, is_api, permutation, m)
            elements['modules'] =  modules
    else:
        elements = build_child_hash_element(raw_string, is_api, permutation, module)
        
    string['string'] = elements
    hash.update(string)

    return hash


def build_child_hash_element(raw_string, is_api, permutation, module_value):
    """
    Build a child element for the hash json object.
    It could be an api endpoint, module name itself or a value from strings.txt
    """

    child_element = {}
    if is_api:
        # result is API
        child_element['string'] = generate_permutation(permutation, api=raw_string, module=module_value)  # noqa:E501
        child_element['is_api'] = True if is_api else False
        child_element['permutation'] = permutation
        child_element['api'] = raw_string
    else:
        # result is module or string
        child_element['string'] = generate_permutation(permutation, module=raw_string, string=raw_string)  # noqa:E501
        child_element['is_api'] = True if is_api else False
        return child_element

    return child_element


def build_hit_element(count, algorithm):
    """
    build hit element (json).
    It contains:
    ### algorithm -> which algorithm matched
    ### count -> how many searched hashes contains to the algorithm
    ### hitrate -> not implemented yet
    """

    elements = {}
    elements['count'] = count
    elements['algorithm'] = algorithm
    # not implemented yet because not important for plugin I guess
    elements['hitrate'] = 0

    return elements


def generate_permutation(permutation, **kwargs):

    keywords = permutation.split('_')
    result = ''
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

        result = result + value

    return result


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
