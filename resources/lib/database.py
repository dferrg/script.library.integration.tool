#!/usr/bin/python
# -*- coding: utf-8 -*-

'''Defines the DatabaseHandler class'''

import sqlite3

from os.path import join

from resources import NEVER
from resources import ALWAYS
from resources import WITH_EPID
from resources import WITH_METADATA

from resources import AUTO_ADD_MOVIES
from resources import AUTO_ADD_TVSHOWS

from resources.lib import build_json_item
from resources.lib import build_contentitem
from resources.lib import build_contentmanager

from resources.lib.log import logged_function

from resources.lib.utils import utf8_args
from resources.lib.utils import MANAGED_FOLDER

from resources.lib.items.blocked import BlockedItem
from resources.lib.items.synced import SyncedItem


class Database(object):
    '''Database class with all database methods.'''

    #TODO: Reimplement blocked keywords
    #TODO: Combine remove_content_item functions using **kwargs
    #TODO: use movie, tvshow as a table_name,
    #the __init__ method to create tables need be updated,
    #the objective is reduce the if's in all plaves
    def __init__(self):
        # Connect to database
        self.conn = sqlite3.connect(join(MANAGED_FOLDER, 'managed.db'))
        self.conn.text_factory = str
        self.cur = self.conn.cursor()
        # Create tables if they doesn't exist
        self.cur.execute(
            '''CREATE TABLE IF NOT EXISTS movie
            (
                file TEXT PRIMARY KEY,
                title TEXT,
                type TEXT,
                status TEXT,
                year TEXT
            )'''
        )

        self.cur.execute(
            '''CREATE TABLE IF NOT EXISTS tvshow
            (
                file TEXT PRIMARY KEY,
                title TEXT,
                type TEXT,
                status TEXT,
                year TEXT,
                showtitle TEXT,
                season TEXT,
                episode TEXT
            )'''
        )
        # FUTURE: Add a music table, for stage and add musics
        self.cur.execute(
            '''CREATE TABLE IF NOT EXISTS synced
            (
                file TEXT PRIMARY KEY,
                label TEXT,
                type TEXT
            )'''
        )
        self.cur.execute(
            '''CREATE TABLE IF NOT EXISTS blocked
            (
                value TEXT NOT NULL,
                type TEXT NOT NULL
            )'''
        )
        self.conn.commit()


    def __del__(self):
        # Close connection when deleted
        self.conn.close()


    @utf8_args
    @logged_function
    def add_blocked_item(self, value, _type):
        '''Add an item to blocked with the specified values'''
        # Ignore if already in table
        if not self.check_blocked(value, _type):
            self.cur.execute("INSERT INTO blocked (value, type) VALUES (?, ?)", (value, _type))
            self.conn.commit()


    @utf8_args
    @logged_function
        '''Add content to library'''
    def add_content_item(self, jsondata, mediatype):
        ''' Add content to library '''
        query_defs = ''
        params = ''
        if mediatype == 'tvshow':
            # try set params for tvshow episode
            params = (
                jsondata['link_stream_path'],
                jsondata['episode_title'],
                mediatype,
                jsondata['year'],
                jsondata['show_title'],
                jsondata['season_number'],
                jsondata['episode_number'],
            )
            query_defs = (
                "Tvshows",
                "(Directory, Title, Mediatype, Status, Year, Show_Title, Season, Epnumber)",
                "(?, ?, ?, 'staged', ?, ?, ?, ?)"
            )
        elif mediatype == 'movie':
            # try set params for movie
            params = (
                jsondata['link_stream_path'],
                jsondata['movie_title'],
                mediatype,
                jsondata['year'],
            )
            query_defs = (
                "Movies",
                "(Directory, Title, Mediatype, Status, Year)",
                "(?, ?, ?, 'staged', ?)"
            )
        elif mediatype == 'music':
            # TODO: Music params
            raise NotImplementedError(
                'Not detected type!'
            )

        # Define sql command string
        sql_comm = ('''INSERT OR IGNORE INTO %s %s VALUES %s''' % query_defs)
        # Execute and commit sql command
        self.cur.execute(sql_comm, params)
        self.conn.commit()
        # Optionally add item to directory, depending on settings and metadata items

        try:
            content = ContenMovie(jsondata)
        except Exception as e:
            content = ContentShow(jsondata)
            log_msg(e)

        if mediatype == 'movie' and AUTO_ADD_MOVIES != NEVER:
            if AUTO_ADD_MOVIES == ALWAYS:
                content.add_to_library()
            elif AUTO_ADD_MOVIES == WITH_METADATA:
                content.add_to_library_if_metadata()
        elif mediatype == 'tvshow' and AUTO_ADD_TVSHOWS != NEVER:
            if AUTO_ADD_TVSHOWS == WITH_EPID:
                content.add_to_library()
            elif AUTO_ADD_TVSHOWS == WITH_METADATA:
                content.add_to_library_if_metadata()

    @utf8_args
    @logged_function
    def add_synced_dir(self, label, path, _type):
        '''Create an entry in synced with specified values'''
        self.cur.execute(
                    (?, ?, ?)''', (path, label, _type)
        )
        self.conn.commit()


    @utf8_args
    @logged_function
    def check_blocked(self, value, _type):
        '''Return True if the given entry is in blocked'''
        # TODO: test if fetchone ir realy working
                                type=?''', (value, _type))


    @logged_function
    def get_all_shows(self, status):
        '''Query Content table for all (not null) distinct showtitles
        and cast results as list of strings'''
        # Query database
        self.cur.execute(
            '''SELECT DISTINCT Show_Title FROM Tvshows WHERE Status=?
            ORDER BY (CASE WHEN Show_Title LIKE 'the %' THEN substr(Show_Title,5)
            ELSE Show_Title END) COLLATE NOCASE''', (status, )
        )
        # Get results and return items as list
        return [x[0] for x in self.cur.fetchall() if x[0] is not None]


    @logged_function
    def get_blocked_items(self):
        '''Return all items in blocked as a list of BlockedItem objects'''
        return [BlockedItem(*x) for x in self.cur.fetchall()]


    @logged_function
    def get_content_items(self, status=None, _type=None):
        '''Query Content table for sorted items with given constaints
        and casts results as contentitem subclasses
        keyword arguments:
            status: string, 'managed' or 'staged'
            _type: string, 'movie' or 'tvshow'
            showtitle: string, any show title
            order: string, any single column'''
                            status="%s"''' % (_type, status))

            if (season_number is None and
                    show_title is not None):
                params += (show_title, )
                sql_comm += ' AND Show_Title=? \
                    ORDER BY CAST(Season AS INTEGER), \
                    CAST(Epnumber AS INTEGER)'

            if show_title is None:
                sql_comm += ' ORDER BY Show_Title, \
                    CAST(Season AS INTEGER), \
                    CAST(Epnumber AS INTEGER)'

        if order == 'Season':
            params += (show_title, )
            sql_comm = sql_comm.replace('*', 'DISTINCT CAST(Season AS INTEGER)')
            sql_comm += ' and Show_Title=? ORDER BY CAST(Season AS INTEGER)'

        if order == 'Title':
            sql_comm += ' ORDER BY Title'
        self.cur.execute(sql_comm, params)
        # Get results and return items as content items
        return [self.content_item_from_db(x) for x in self.cur.fetchall()]


    @utf8_args
    @logged_function
    def get_synced_dirs(self, synced_type=None):
        '''Get all items in synced cast as a list of dicts'''
        # Define template for this sql command
        sql_templ = 'SELECT * FROM Synced'
        params = ()
        if synced_type:
            sql_templ += ' WHERE Type=?'
            params = (synced_type, )
        sql_templ += ''' ORDER BY (CASE WHEN Label LIKE 'the %' THEN substr(Label,5)
            ELSE Label END) COLLATE NOCASE'''
        # query database
        self.cur.execute(sql_templ, params)
        # get results and return as list of dicts
        return [SyncedItem(*x) for x in self.cur.fetchall()]


    @utf8_args
    @logged_function
    def load_item(self, path):
        '''Query a single item with path and casts result as contentitem subclasses'''
        # query database
        self.cur.execute('SELECT * FROM Content WHERE Directory=?', (path, ))
        # get results and return items as object
        return self.content_item_from_db(self.cur.fetchone())


    @utf8_args
    @logged_function
       '''Return True if path is already in database (with given status)
            This function can return a list with multple values 
            with name of the tables where item exist'''
            sql_comm = (
                "SELECT (Directory) FROM {0} \
                    WHERE Directory = '{1}' \
                    AND Status = '{2}'".format(
                        table_name,
                        path,
                        item
                    )
            )
        return bool(self.cur.execute(sql_comm).fetchone())

    # @logged_function
    # def remove_all_content_items(self, status, mediatype):
    #     '''Remove all items from Content with status and mediatype'''
    #     # delete from table
    #     self.cur.execute(
    #         "DELETE FROM Content \
    #         WHERE Status=? AND Mediatype=?",
    #         (status, mediatype))
    #     self.conn.commit()

    # @utf8_args
    # @logged_function
    #     '''Remove all tvshow items from Content with status and showtitle'''
    #     # delete from table
    #     self.cur.execute(
    #         "DELETE FROM Content \
    #         WHERE Status=? AND Show_Title=?",
    #         (status, show_title)
    #     )
    #     self.conn.commit()

    # @utf8_args
    # @logged_function
    # def remove_content_item(self, path):
    #     '''Remove the item in Content with specified path'''
    #     # delete from table
    #     self.conn.commit()


    @utf8_args
    @logged_function
    def remove_from(self,
                    status=None,
                    _type=None,
                    directory=None,
                    season=None):
        '''Remove all items colected with sqlquerys'''
        STR_CMD_QUERY = "DELETE FROM {0} %s".format(_type)
        else:
            # FUTURE: check if is music
            raise 'Type not detected'

        STR_CMD_QUERY = "DELETE FROM {0} %s".format(table_name)

        if show_title is not None:
            self.cur.execute(
                (
                    STR_CMD_QUERY % "WHERE Status=? AND Show_Title=?"
                ), (status, show_title)
            )
        if show_title is None and directory is None:
            self.cur.execute(
                (
                    STR_CMD_QUERY % "WHERE Status=? AND Mediatype=?"
                ), (status, mediatype)
            )
        if directory is not None:
            self.cur.execute(
                (
                    STR_CMD_QUERY % "WHERE Directory=?"
                ), (directory, )
            )
        if season is not None:
            self.cur.execute(
                (
                    STR_CMD_QUERY % "WHERE Show_Title=? AND Season=?"
                ), (show_title, season)
            )
        self.conn.commit()


    @logged_function
    def remove_all_synced_dirs(self):
        '''Delete all entries in synced'''
        # remove all rows
        self.cur.execute('DELETE FROM Synced')
        self.conn.commit()

    @utf8_args
    @logged_function
    def remove_blocked(self, value, _type):
        '''Remove the item in blocked with the specified parameters'''
        self.cur.execute(
            (value, _type)
        )
        self.conn.commit()

    @utf8_args
    @logged_function
    def remove_synced_dir(self, path):
        '''Remove the entry in synced with the specified file'''
        # remove entry
        self.cur.execute(
            "DELETE FROM Synced WHERE Directory=?",
            (path, )
        )
        self.conn.commit()

    @utf8_args
    @logged_function
    def update_content(self, file, _type, status=None, title=None):
        '''Update a single field for item in Content with specified path'''
        #TODO: Verify there's only one entry in kwargs
        sql_comm = (
            '''UPDATE %s SET {0}=(?) WHERE file=?''' % _type
        )
        params = (path, )

        for key, val in kwargs.items():
            if key == 'status':
                sql_comm = sql_comm.format('Status')
            elif key == 'title':
                sql_comm = sql_comm.format('Title')
            params = (val, ) + params
        # update item
        self.cur.execute(sql_comm, params)
        self.conn.commit()
