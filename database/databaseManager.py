import sqlite3
import json

SQL_SCHEMA = """
CREATE TABLE IF NOT EXISTS version_control (
    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_description TEXT,
    version_charsize INTEGER
);

CREATE TABLE IF NOT EXISTS classes (
    class_id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_name TEXT NOT NULL,
    class_description TEXT
);

CREATE TABLE IF NOT EXISTS items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_name TEXT NOT NULL,
    item_type TEXT NOT NULL,
    item_description TEXT
);

CREATE TABLE IF NOT EXISTS changelog (
    internal_id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id INTEGER NOT NULL REFERENCES version_control(version_id),
    content_type TEXT NOT NULL CHECK (content_type IN ('item', 'class')),
    content_id INTEGER NOT NULL,
    change_type TEXT NOT NULL CHECK (change_type IN ('ADD', 'EDIT', 'DELETE')),
    contents TEXT
);

CREATE INDEX index_changelog_version ON changelog (version_id)
"""

class Database:
    def __init__(self):
        try:
            self.connection = sqlite3.connect('mainDatabase.db')
            self.cursor = self.connection.cursor()

            self.connection.executescript(SQL_SCHEMA)

            print(self.connectionVerifier(self.cursor))
            self.databaseInitialized = True
        except sqlite3.Error as error:
            print('An Error Occured on Database Initialization: ', error)
            self.databaseInitialized = False

    def connectionVerifier(self, cursor):
        basicQuery = 'SELECT sqlite_version();'
        cursor.execute(basicQuery)
        
        result = cursor.fetchall()
        return('SQLite is running and the version is {}'.format(result[0][0]))

    def writeVersion(self, versionDescription: str, version: dict):
        print()

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
            "class":"c"
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
