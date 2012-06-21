#!/usr/bin/python3

# Standart library modules
import argparse
import logging
import sqlite3

# Project modules
import path_model

__version__ = '0.1.1'


def get_arguments():
    arg = argparse.ArgumentParser(description='Simplify paths: remove unsused points, try to find similiar paths.')
    arg.add_argument('--db', default='data.sqlite', help='Path to database with paths.')
    arg.add_argument('--db-schema', default='db_schema.sql', type=argparse.FileType('r'),
            help='Database schema. Used if database file doesn''t exist.')
    arg.add_argument('--tracks', default='', type=str, help='Comma separated list of tracks to simplify. Use traack id from database.')
    return arg.parse_args()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    args = get_arguments()
    # db


