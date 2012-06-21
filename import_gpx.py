#!/usr/bin/python3

import argparse
import sqlite3
import pprint
from lxml import etree
import cairo
import math

__version__ = '0.1.1'


def get_arguments():
    # Parse commandline arguments.
    argparser = argparse.ArgumentParser(description='Convert GPX trackpoints to maps.')
    argparser.add_argument('--version', action='version', version='%(prog)s ' + __version__)
    argparser.add_argument('gpx', nargs='+', type=argparse.FileType('r'),
        help='GPX files to import.')
    argparser.add_argument('--db', default='data.sqlite')
    argparser.add_argument('--db-schema', default='db_schema.sql', type=argparse.FileType('r'))
    return argparser.parse_args()


def create_db(db_file, db_schema):
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.executescript(db_schema.read(-1))
    db_schema.close()
    c.close()
    return conn


def getTrackIdByName(cursor, track_name):
    cursor.execute('select id from tracks where name = :n', {'n': track_name})
    result = cursor.fetchone()
    if result is not None:
        return result[0]
    else:
        return None


def import_gpx(db, fObj):
    xml_data = etree.parse(fObj)
    namespaces = {'g': 'http://www.topografix.com/GPX/1/1',
                  'gpxx': 'http://www.garmin.com/xmlschemas/GpxExtensions/v3',
                  'gpxtpx': 'http://www.garmin.com/xmlschemas/TrackPointExtension/v2'  }
    cursor = db.cursor()
    for track_xml in xml_data.xpath('/g:gpx/g:trk', namespaces=namespaces):
        track_name = track_xml.xpath('g:name', namespaces=namespaces)[0].text
        cursor.execute('select id from tracks where name = :n', {'n': track_name})
        track_exists = cursor.fetchone() is not None
        if track_exists:
            print('Found track {0} but it already exists.'.format(track_name))
            continue
        
        cursor.execute('insert into tracks(name) values(:n)', {'n': track_name})
        points_xml = track_xml.xpath('g:trkseg/g:trkpt', namespaces=namespaces)
        track_id = getTrackIdByName(cursor, track_name)
        for point_xml in points_xml:
            params = {
                'lat': point_xml.get('lat'),
                'lon': point_xml.get('lon'),
                'ele': float(point_xml.xpath('g:ele', namespaces=namespaces)[0].text),
                'time': point_xml.xpath('g:time', namespaces=namespaces)[0].text,
                'track': track_id
            }

            course_elem =  point_xml.xpath('g:extensions/gpxtpx:TrackPointExtension/gpxtpx:course', namespaces=namespaces)
            params['course'] = course_elem[0].text if len(course_elem) > 0 else None

            speed_elem = point_xml.xpath('g:extensions/gpxtpx:TrackPointExtension/gpxtpx:speed', namespaces=namespaces)
            params['speed'] = speed_elem[0].text if len(speed_elem) > 0 else None

            cursor.execute('''insert into track_points
                              (lat, lon, elevation, time, course, speed, track)
                              values(:lat, :lon, :ele, :time, :course, :speed, :track)''',
                           params)
            
        print('Found track {0} with {1} points.'.format(track_name, len(points_xml)))

    db.commit()
    cursor.close()


if __name__ == '__main__':
    args = get_arguments()
    db = create_db(args.db, args.db_schema)
    for fObj in args.gpx:
        print('Working with file {0}.'.format(fObj.name))
        import_gpx(db, fObj)
        fObj.close()
    db.close()
