#!/usr/bin/python3

import argparse
import gzip
import math
import os.path
import sqlite3

import cairo

#import track_db


__version__ = '0.1.1'


def get_arguments():
    # Parse commandline arguments.
    argparser = argparse.ArgumentParser(description='Convert GPX trackpoints to maps.')
    argparser.add_argument('--version', action='version', version='%(prog)s ' + __version__)
    argparser.add_argument('--db', default='data.sqlite')
    argparser.add_argument('--db-scheme', default='db_schema.sql', type=argparse.FileType('r'))
    argparser.add_argument('-o', '--output', default='image.svg', type=argparse.FileType('wb'))
    argparser.add_argument('--width', default=700, type=int)
    argparser.add_argument('--height', default=700, type=int)
    argparser.add_argument('--padding', default=20, type=int)
    return argparser.parse_args()


def create_db(db_file, db_scheme):
    db = sqlite3.connect(db_file)
    c = db.cursor()
    c.executescript(db_scheme.read(-1))
    db_scheme.close()
    c.close()
    return db


def getTrackIdByName(cursor, track_name):
    cursor.execute('select id from tracks where name = :n', {'n': track_name})
    result = cursor.fetchone()
    if result is not None:
        return result[0]
    else:
        return None


if __name__ == '__main__':
    # Init application.
    args = get_arguments()
    db = create_db(args.db, args.db_scheme)

    # Decide whether to compress output.
    if os.path.splitext(args.output.name)[1] == '.svgz':
        output_stream = gzip.GzipFile(fileobj=args.output)
    else:
        output_stream = args.output

    # Init drawing objects.
    surface = cairo.SVGSurface(output_stream, args.width, args.height)
    ctx = cairo.Context(surface)

    # Fill background.
    ctx.set_source_rgb(0, 0, 0)
    ctx.paint()

    # Prepare to draw lines.
    ctx.set_source_rgb(100, 0, 0)
    ctx.set_line_width(1)
    
    # Get extreme values.
    c = db.cursor()
    c.execute('select max(lat), max(lon), min(lat), min(lon) from track_points')
    max_lat, max_lon, min_lat, min_lon = c.fetchone()
    scale = min( (args.width - args.padding * 2) / (max_lon - min_lon),
                 (args.height - args.padding * 2) / (max_lat - min_lat))
   
    # Get all values.     
    c.execute('select lat, lon, track from track_points order by track, id')
    prev_lat, prev_lon, track_id  = c.fetchone()
    row = c.fetchone()
    while row is not None:
        if row[2] == track_id:
            ctx.move_to((prev_lon - min_lon) * scale + args.padding,
                        (max_lat - prev_lat) * scale + args.padding)
            ctx.line_to((row[1] - min_lon) * scale + args.padding,
                        (max_lat - row[0]) * scale + args.padding)
            #ctx.move_to((prev_lon - min_lon) * scale, - (max_lat - prev_lat) * scale / math.cos(prev_lat))
            #ctx.line_to((row[1] - min_lon) * scale, - (max_lat - row[0]) * scale/math.cos(row[0]))
            ctx.stroke()
        prev_lat, prev_lon, track_id  = (row[0], row[1], row[2])
        row = c.fetchone()
    surface.finish()
    c.close()
    db.close()
    output_stream.close() 


