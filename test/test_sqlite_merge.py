#!/usr/bin/env python

import unittest
import os
import sqlite3
import sys
sys.path.append( '../lib/' )
import SQLite

class TestSQLite(unittest.TestCase):

    def removeFile(self, file):
        #delete a file if it exists
        if os.path.isfile(file):
            os.system("rm {file}".format(file=file))

    def createFile(self, file, type=None, data="1,2,3"):
        #create a file db, csv
        if file.split(".")[-1] == "db" or type == "db":
            conn = sqlite3.connect(file)
            c = conn.cursor()
            c.executescript(""" 
                CREATE TABLE test (a, B, c);
                CREATE TABLE main (d, E, f);
                INSERT INTO test VALUES ({data});
                INSERT INTO main VALUES ({data});
                CREATE INDEX idx ON test (a);
                CREATE INDEX idy ON test (a, b);
                """.format(data=data)) #"""
            conn.commit()
            c.close()
            conn = sqlite3.connect(file)
        elif file.split(".")[-1] == "csv" or type == "csv":
            os.system("echo '{data}' >> {file}".\
                format(data=data, file=file))

    def setUp(self):
        self.removeFile("test.db")
        self.removeFile("test.csv")
        self.removeFile("test2.db")
        self.removeFile("test2.csv")
        # create a really basic dataset
        self.createFile(file="test.db")
        self.s = SQLite.SQLite(db="test.db", tbl="test")
        self.createFile("test2.db")
        s = SQLite.SQLite("test2.db", tbl="test")
        self.s.attach(s)

    def tearDown(self):
        self.removeFile("test.db")
        self.removeFile("test.csv")
        self.removeFile("test2.db")
        self.removeFile("test2.csv")
        self.removeFile("errlog")


    def test_indexes(self):
        self.assertIn('idx', self.s.indexes())
        self.assertTrue(self.s.indexes(lookup="idx"))
        self.assertFalse(self.s.indexes(lookup="xdi"))
        self.assertEquals([0,0], self.s.indexes(seq="xdi"))
        self.assertEquals([1,1], self.s.indexes(seq="idx"))
        self.s.c.executescript(""" 
            CREATE INDEX idx1 ON test (b);
            CREATE INDEX idx2 ON test (c);
            CREATE INDEX idx5x3 ON test (a);
            CREATE INDEX idx10x ON test (a);
            """)
        self.assertEquals([1,3], self.s.indexes(seq="idx"))

    def test__baseIndex(self):
        self.assertItemsEqual(['test (a)', 'test (a,b)'],
            self.s._baseIndex(db="db"))
        self.assertEqual('test (a)',
            self.s._baseIndex(idx="idx"))
        self.assertEqual('foo (bar,foo)',
            self.s._baseIndex(idx="create index x on foo (foo, bar)"))
        self.assertEqual('unique foo (foo)',
            self.s._baseIndex(idx="create unique index x on foo (foo)"))


    def test_index(self):
        self.s.index([['a','c']])
        self.assertIn('test (a,c)', self.s._baseIndex())
        self.s.index('a', unique=True)
        self.assertIn('test (a)', self.s._baseIndex())
        self.assertFalse(self.s.index(['a','c']))
        self.s.index('f', tbl="main")
        self.assertIn('main (f)', self.s._baseIndex())
        self.assertFalse(self.s.index('a', tbl="main"))
        #self.s.index(['e', 'f'], combo=True, tbl="main")
        #self.assertIn('main (e)', self.s._baseIndex(tbl="main"))
        #self.assertIn('main (e,f)', self.s._baseIndex(tbl="main"))

        self.s.index([['a','c']], db="db")
        self.assertIn('test (a,c)', self.s._baseIndex(db="db"))

#    def test_merge(self):
#        s = SQLite.SQLite()
#        s.merge(key=[['AsgNum', 'pdpass']], on=[['assigneeAsc', 'assignee']],
#                keyType=['INTEGER'], tableFrom='main', db='db')
#        assert(1 == 1)


if __name__ == '__main__':
    unittest.main()

