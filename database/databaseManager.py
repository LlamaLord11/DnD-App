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
        All code uses this index for versioning, the alternative display_version is purely for clients/public viewing and has no internal use.
        The display version is a decimal that increments by 0.1 for each new version, starting at 0"""
        lastVersion = self.readLatestDisplayVersion()

        if not lastVersion: lastVersion = '0.0'

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

    def formatChangelogRow(self, currentRow: list, rowNameList: list) -> dict:
            outputDict = {}
            for i in range(0,len(currentRow) - 1):
                outputDict[rowNameList[i]] = currentRow[i]

            outputDict[rowNameList[-1]] = json.loads(currentRow[-1])
    
            return outputDict

    def readSingleVersion(self, version: int) -> list:
        """Returns a LIST of all changelog entries pertaining to the provided version.

        FORMAT: { internal_id: internal_id (autoincriment SQL index), version_id: version_id, 
        content_id: content_id (specific entry ID), content_type: content_type (item/class/spell), 
        change_type: change_type (ADD/EDIT/DELETE), contents: contents (another dictionary containing all rows not explicitly listed) }"""

        base_info = self.cursor.execute('PRAGMA table_info(changelog)')
        columnNames = [col[1] for col in base_info]

        self.cursor.execute('SELECT * FROM changelog WHERE version_id = ?', (version,))
        versionList = self.cursor.fetchall()
        formattedVersionList = []

        for row in versionList:
            formattedVersionList.append(self.formatChangelogRow(row, columnNames))

        return formattedVersionList

    # def versionListFormatterOld(self, versionList):
    #     """Outputs a list of lists. Each internal list represents 1 entry
    #     \nENTRY FORMATTING: change_type (ADD + / EDIT > / DELETE -), content_type (item i / class c), content_id, content"""

    #     change_type_hash = {
    #         "ADD":"+",
    #         "EDIT":'>',
    #         "DELETE":"-"
    #     }

    #     content_type_hash = {
    #         "item":"i",
    #         "class":"c",
    #         "spell":"s"
    #     }

    #     formatedList = []

    #     for row in versionList:
    #         formatedList.append([change_type_hash[row[4]], content_type_hash[row[2]], row[3], json.loads(row[5])])

    #     return json.dumps(formatedList, separators=(',', ':'))

    def jsonStringMaker(self, inputDictionary):
        # No need to hash ADD/EDIT/DELETE/Table type. At scale, it is a negligable data size reduction
        return json.dumps(inputDictionary, separators=(',', ':'))

        

    def cacheCreator(self) -> dict:
        """Creates the cache (dictionary format) of all versions the client will pull from for syncing"""
        versionCache = {}

        self.cursor.execute('SELECT version_id FROM version_control')
        listOfVersions = self.cursor.fetchall()

        for (versionID,) in listOfVersions:
            currentVersion = self.readSingleVersion(versionID)
            formattedVersion = self.jsonStringMaker(currentVersion)
            versionCache[versionID] = formattedVersion

        return versionCache


    def close(self):
        self.connection.close()

"""
Quick planning section on the data formatting
Changelog contents section may as well just be a formatted json string as it needs to contain a dictonary of things which in just text would
loose all formatting. In json string format, it can easily be reverted back to a dictionary without me needing to build my own text format system
to recognize what represents what as well as how to seperate each dictionary item, etc...

What that means is that I need a function that takes in a dictionary and turns it into a json string.

This is all neccesary as my changelong system needs to be able to accept a variable number of columns in the contents section as each internal table
can vary in column count. ex: class has 3 columns while spells and items have 4. This will get more drastic as time passes and I begin to rewrite the
database structure to actually handle the data they need to hold. The current iteration is effectively just a placeholder as I don't know what the
final data going in will look like. Better to make it flexible now to avoid unneccesary server/backend rewrites.
"""

db = Database()
db.databaseWriter("dummystring", ['dummyList'])
