import pefile
import sqlite3
import os
import glob
import sys


def get_db(path):
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE IF NOT EXISTS functions (name text, dll text, ordinal int)")
    return db


def add_function(cursor, dll, name, ordinal):
    cursor.execute("INSERT INTO functions(name, dll, ordinal) VALUES (?, ?, ?)", (name, dll, ordinal))


def main():
    if len(sys.argv) != 3:
        print("Usage: {:s} <directory_or_file> <db path>".format(sys.argv[0]))
        return

    path, db_path = sys.argv[1:]
    if not os.path.exists(path):
        print("'{:s}' does not exist".format(path))
        return

    if os.path.isfile(path):
        filenames = [path]
    else:
        filenames = glob.glob(os.path.join(path, "*.[dD][lL][lL]"))
        filenames.sort()

    db = get_db(db_path)
    cursor = db.cursor()

    for filename in filenames:
        d = [pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]]
        pe = pefile.PE(filename, fast_load=True)
        pe.parse_data_directories(directories=d)

        dll = os.path.basename(filename)

        print("Adding {:d} exports from {:s} to database...".format(
            len(pe.DIRECTORY_ENTRY_EXPORT.symbols), dll))

        for e in pe.DIRECTORY_ENTRY_EXPORT.symbols:
            ordinal = e.ordinal
            name = e.name
            if name:
                name = name.decode()

            add_function(cursor, dll, name, ordinal)

    db.commit()
    cursor.close()

    db.close()


if __name__ == "__main__":
    main()
