# HashDB-Hook
This HashDB-Hook can be used as replacement of the `requests` module, so that the original implementaion of the [HashDB-Plugin](../hashdb.py) doesn't has to be adapted more than changing the import as is done with the patch file.

The hook implements the requests methods like `get` and `post` and processes the requests analogous to the HashDB-Lookup-Service using the local database.

## HashDB Lookup Service Replacement (to be used in the [IDA-Plugin](../hashdb.py))
### get > /hash
Get available hash alorithms
### get > /hash/`<algorithm>`/`<hash>`
Get strings corresponding to the algorithm hash combination
### get > /module/`<module>`/`<permutation>`
Get list of API string permutations for module
### post > /hunt
Identify algorithms containing hashes: Returns hits for matching algorithm hashes

Payload:
```
{
  "hashes": [
    0
  ]
}
```