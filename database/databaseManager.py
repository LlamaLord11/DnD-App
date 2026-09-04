import sqlite3
import json
import decimal

# Table Formatting Notes
# All client usable data should be formatted as follows
# content_id NOT NULL, content_name NOT NULL, trailing additional and optional fields which may vary by table

'''
Going to need a broad scale modification of systems to account for the write system
'''

SQL_SCHEMA = """
CREATE TABLE IF NOT EXISTS version_control (
    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
    display_version_id TEXT NOT NULL,
    version_description TEXT,
    version_charsize INTEGER
);

CREATE TABLE IF NOT EXISTS class (
    content_id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_name TEXT NOT NULL,
    class_description TEXT
);

CREATE TABLE IF NOT EXISTS item (
    content_id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_name TEXT NOT NULL,
    item_type TEXT,
    item_description TEXT
);

CREATE TABLE IF NOT EXISTS spell (
    content_id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_name TEXT NOT NULL,
    spell_school TEXT,
    spell_description TEXT
);

CREATE TABLE IF NOT EXISTS changelog (
    internal_id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id INTEGER NOT NULL REFERENCES version_control(version_id),
    content_id INTEGER NOT NULL,
    content_type TEXT NOT NULL CHECK (content_type IN ('item', 'class', 'spell')),
    change_type TEXT NOT NULL CHECK (change_type IN ('ADD', 'EDIT', 'DELETE')),
    contents TEXT
);

CREATE INDEX index_changelog_version ON changelog (version_id)
"""

# NOTE: Contents inside changelogs is a variable length list that contains all columns excluding the content_id and content_name

TABLENAME_WHITELIST = ["class", "item", "spell"]

class Database:
    def __init__(self):
        try:
            self.connection = sqlite3.connect('mainDatabase.db')
            self.cursor = self.connection.cursor()

            self.connection.executescript(SQL_SCHEMA)

            print(self.connectionVerifier(self.cursor))

            self.columnList = {} # FORMAT: "Table Name" : [List of Columns]
            self.dbInitColumnNames() # Writes to columnList

            self.databaseInitialized = True
        except sqlite3.Error as error:
            print('An Error Occured on Database Initialization: ', error)
            self.databaseInitialized = False

    def connectionVerifier(self, cursor):
        basicQuery = 'SELECT sqlite_version();'
        cursor.execute(basicQuery)
        
        result = cursor.fetchall()
        return('SQLite is running and the version is {}'.format(result[0][0]))

    # System Writing Pipeline Mockup
    # OVERVIEW: JSON File -> list -> database write

    def jsonFileReader(self, path: str):
        """path MUST be a raw string"""
        try:
            with open(path) as file:
                file = json.load(file)

            return file
        except:
            return False

    def databaseWriter(self, versionDescription: str, versionContents: dict):

        versionCharsize = 0

        currentVersionID = self.version_control_writer(versionDescription, versionCharsize)

    def version_control_writer(self, version_description: str, version_charsize: int) -> int:
        """Writes the basic version_control table entry and returns the current internal version index. 
        All code uses this index for versioning, the alternative display_version is purely for clients/public viewing and has no bearing on code"""
        lastVersion = self.readLatestDisplayVersion()

        if not lastVersion:
            lastVersion = '0.0'

        currentVersion = decimal.Decimal(lastVersion) + decimal.Decimal('0.1')
        formattedDecimal = str(currentVersion)
        self.cursor.execute(f'INSERT INTO version_control (display_version_id, version_description, version_charsize) VALUES (?, ?, ?) RETURNING version_id', [formattedDecimal, version_description, version_charsize])
        versionID = self.cursor.fetchone()[0]

        return versionID

    def dbInitColumnNames(self):
        for table_name in TABLENAME_WHITELIST:
            base_info = self.cursor.execute(f'PRAGMA table_info({table_name})')
            columnNames = [col[1] for col in base_info]

            self.columnList[table_name] = columnNames

    def databaseADD(self, table: str, input_values: list):
        self.cursor.execute(f'INSERT INTO {table} ({", ".join(self.columnList[table][1:])}) VALUES ({"?"+(", ?"*(len(input_values) - 1))})', input_values)

    def databaseEDIT(self, table: str, input_values: list, content_id: int):
        self.cursor.execute(f'UPDATE {table} SET {" = ?, ".join(self.columnList[table][1:])} = ? WHERE {self.columnList[table][0]} = ?', (input_values + [content_id]))

    def databaseDELETE(self, table: str, content_id: int):
        self.cursor.execute(f'DELETE FROM {table} WHERE {self.columnList[table][0]} = ?', (content_id,))
        
    def readLatestDisplayVersion(self) -> str:
        self.cursor.execute('SELECT display_version_id FROM version_control ORDER BY version_id DESC LIMIT 1')
        result = self.cursor.fetchone()
        if result:
            result = result[0]
        else:
            result = None

        return result

# TABLE FORMATTING: content_id NOT NULL, content_name NOT NULL, trailing additional and optional fields which may vary by table
# CHANGELOG FORMATTING: internal_id (Changelog key), version_id (version_control table index link), content_id (sub table id (classes/items/spells)), content_type (item/spell/class), change_type (ADD/EDIT/DELETE), contents
# - CONTENTS CONT: contents is a list that will contain all columns in order of each table excluding the content_id. The first item will always be the name.

    def readSingleVersion(self, version: int) -> list:
        """Returns a LIST of all changelog entries pertaining to the provided version.
        \nFORMAT: [ internal_id (autoincriment SQL index), version_id, content_type (item/class), content_id (specific entry ID), change_type (ADD/EDIT/DELETE), contents ]"""
        self.cursor.execute('SELECT * FROM changelog WHERE version_id = ?', (version,))
        versionList = self.cursor.fetchall()

        return versionList

    def versionListFormatter(self, versionList):
        """Outputs a list of lists. Each internal list represents 1 entry
        \nENTRY FORMATTING: change_type (ADD + / EDIT > / DELETE -), content_type (item i / class c), content_id, content"""

        change_type_hash = {
            "ADD":"+",
            "EDIT":'>',
            "DELETE":"-"
        }

        content_type_hash = {
            "item":"i",
            "class":"c",
            "spell":"s"
        }

        formatedList = []

        for row in versionList:
            formatedList.append([change_type_hash[row[4]], content_type_hash[row[2]], row[3], json.loads(row[5])])

        return json.dumps(formatedList, separators=(',', ':'))

        

    def cacheCreator(self) -> dict:
        """Creates the cache (dictionary format) of all versions the client will pull from for syncing"""
        versionCache = {}

        self.cursor.execute('SELECT version_id FROM version_control')
        listOfVersions = self.cursor.fetchall()

        for (versionID,) in listOfVersions:
            currentVersion = self.readSingleVersion(versionID)
            formattedVersion = self.versionListFormatter(currentVersion)
            versionCache[versionID] = formattedVersion

        return versionCache


    def close(self):
        self.connection.close()

db = Database()
db.databaseWriter("dummystring", ['dummyList'])
