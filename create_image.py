#!/usr/bin/python3

import argparse
import bisect
import gzip
import logging
import math
import os.path
import sqlite3

import cairo

#import track_db


__version__ = '0.1.1'

IMAGE_TYPE_OLD = 'old'
IMAGE_TYPE_POINTS = 'points'

def get_arguments():
    # Parse commandline arguments.
    argparser = argparse.ArgumentParser(description='Convert GPX trackpoints to maps.')
    argparser.add_argument('--version', action='version', version='%(prog)s ' + __version__)
    argparser.add_argument('--db', default='data.sqlite', help='Path to database file.')
    argparser.add_argument('--db-schema', default='db_schema.sql', type=argparse.FileType('r'),
                           help='Path to file with database schema.')
    argparser.add_argument('-o', '--output', default='image.svg', type=argparse.FileType('wb'),
                           help='Output file path.')
    argparser.add_argument('--width', default=750, type=int, help='Image width in pixels.')
    argparser.add_argument('--height', default=350, type=int, help='Image height in pixels.')
    argparser.add_argument('--padding', default=20, type=int, help='Image internal borders.')
    argparser.add_argument('--tracks', default='', type=str, help='Comma separated list of tracks to draw.')
    argparser.add_argument('-t', '--type', default=IMAGE_TYPE_OLD, type=str,
                           choices=(IMAGE_TYPE_OLD, IMAGE_TYPE_POINTS),
                           help='Type of image to generate.')
    return argparser.parse_args()


def create_db(db_file, db_schema):
    db = sqlite3.connect(db_file)
    c = db.cursor()
    c.executescript(db_schema.read(-1))
    db_schema.close()
    c.close()
    return db


def getTrackIdByName(cursor, track_name):
    cursor.execute('select id from tracks where name = :n', {'n': track_name})
    result = cursor.fetchone()
    if result is not None:
        return result[0]
    else:
        return None


def old_algo(db, args):
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
    #ctx.set_source_rgb(100, 0, 0)
    #ctx.set_line_width(1)
    
    if len(args.tracks) > 0:
        where_tracks = ' where track in ({0}) '.format(args.tracks)
    else:
        where_tracks = ''

    # Get extreme values.
    c = db.cursor()
    c.execute('select max(lat), max(lon), min(lat), min(lon) from track_points' + where_tracks)
    max_lat, max_lon, min_lat, min_lon = c.fetchone()
    scale = min( (args.width - args.padding * 2) / (max_lon - min_lon),
                 (args.height - args.padding * 2) / (max_lat - min_lat))
   
    # Get all values.     
    c.execute('select lat, lon, track from track_points ' + where_tracks + ' order by track, id')
    roundness = 4
    prev_lat, prev_lon, track_id  = c.fetchone()
    prev_lat, prev_lon = (round(prev_lat, roundness), round(prev_lon, roundness))
    row = c.fetchone()
    points_occurence, movements = ({}, {})
    tracks, current_track_count = ([ [ ] ], 0)
    points = {}

    # Add first point to arrays.
    points_occurence['{0}_{1}'.format(prev_lat, prev_lon)] = 0
    points['{0}_{1}'.format(prev_lat, prev_lon)] = [(prev_lat, prev_lon), 0]
    tracks[0].append( (prev_lat, prev_lon) )

    verticals, horiz, points_on_line, overall_points = (0,0,0,0)
    
    while row is not None:
        cur_lat, cur_lon = (round(row[0], roundness), round(row[1], roundness))
        overall_points += 1

        one_the_line = False 
        # Is this point on some other line?
        for move in movements.values():
            if move[1] == move[3]:
                verticals += 1
                continue
            else:
                horiz += 1
            line_k = (move[0] - move[2]) / (move[1] - move[3])
            line_b = move[2] - line_k * move[3]
            if (cur_lat == round(line_k * cur_lon + line_b, roundness) and
               cur_lat >= min(move[0], move[2]) and cur_lat <= max(move[0], move[2]) and
               cur_lon >= min(move[1], move[3]) and cur_lon <= max(move[1], move[3])) :
                #logging.debug('Found point on the line! lat=%s, lon=%s', cur_lat, cur_lon)
                points['{0}_{1}'.format(move[0], move[1])][1] += .5
                points['{0}_{1}'.format(move[2], move[3])][1] += .5
                points_occurence['{0}_{1}'.format(move[0], move[1])] += .5
                points_occurence['{0}_{1}'.format(move[2], move[3])] += .5
                points_on_line += 1
                one_the_line = True
                break

        # Points
        #if one_the_line:
        #    prev_lat, prev_lon, track_id  = (cur_lat, cur_lon, row[2])
        #    row = c.fetchone()
        #    continue

        point_key = '{0}_{1}'.format(cur_lat, cur_lon)
        if point_key in points_occurence:
            points_occurence[point_key] += 1
            points[point_key][1] += 1
        else:
            points_occurence[point_key] = 0
            points[point_key] = [(cur_lat, cur_lon), 0]
        
        if row[2] == track_id:
            # Movements
            movement_key = '{0}_{1}_{2}_{3}'.format(prev_lat, prev_lon, cur_lat, cur_lon)
            if movement_key not in movements:
                movements[movement_key] = (prev_lat, prev_lon, cur_lat, cur_lon)
            
            #ctx.move_to((prev_lon - min_lon) * scale + args.padding,
            #            (max_lat - prev_lat) * scale + args.padding)
            #ctx.line_to((row[1] - min_lon) * scale + args.padding,
            #            (max_lat - row[0]) * scale + args.padding)
            #ctx.move_to((prev_lon - min_lon) * scale, - (max_lat - prev_lat) * scale / math.cos(prev_lat))
            #ctx.line_to((row[1] - min_lon) * scale, - (max_lat - row[0]) * scale/math.cos(row[0]))
            #ctx.stroke()

        else:
            tracks.append([])
            
        tracks[-1].append( (cur_lat, cur_lon) )

        prev_lat, prev_lon, track_id  = (cur_lat, cur_lon, row[2])
        row = c.fetchone()
    
    c.close()
    db.close()

    max_occurence_count = max(points_occurence.values()) # * 2.0
    values = list(points_occurence.values())
    values.sort()
    
    for mvkey in movements:
        mv = movements[mvkey]
        pt1_occurence = points_occurence['{0}_{1}'.format(mv[0], mv[1])]
        pt2_occurence = points_occurence['{0}_{1}'.format(mv[2], mv[3])]
        movement_rating = math.sqrt((pt1_occurence + pt2_occurence) / (max_occurence_count / 2.0))*math.sqrt(max_occurence_count / 2.0)
        ctx.set_source_rgb(movement_rating,
                           1.0 - movement_rating,
                           0)
        ctx.set_line_width(1)
        ctx.move_to((mv[1] - min_lon) * scale + args.padding,
                    (max_lat - mv[0]) * scale + args.padding)
        ctx.line_to((mv[3] - min_lon) * scale + args.padding,
                    (max_lat - mv[2]) * scale + args.padding)
        ctx.stroke()
    
    '''more = 0'''
    '''for point in points.values():
        #rating = point[1] / max_occurence_count
        rating = point[1]
        #if rating < 0.15:
        #    continue
        #more += 1
        pointx = (point[0][1] - min_lon) * scale + args.padding
        pointy = (max_lat - point[0][0]) * scale + args.padding
        #print(rating)
        ctx.set_source_rgb(rating,
                           1.0 - rating,
                           0)
        ctx.set_line_width(1)
        ctx.arc( pointx, pointy, 1 + rating, 0, 2 * math.pi)
        ctx.fill()'''
    '''print(more)
    print(len(points))
    print(values[ math.floor(len(values) / 2) ])'''
    surface.finish()
    output_stream.close() 

    logging.debug('Max point occurence: %s', max_occurence_count)
    logging.debug('verticals: %s, horiz: %s', verticals, horiz)
    logging.debug('points on line: %s/%s', points_on_line, overall_points)


def get_where_clause(args):
    if len(args.tracks) > 0:
        return ' where track in ({0}) '.format(args.tracks)
    else:
        return ' '

def get_extreme_coordinates(cursor, where_clause):
    query = 'select max(lat), max(lon), min(lat), min(lon) from track_points' + where_clause
    cursor.execute(query)
    max_lat, max_lon, min_lat, min_lon = cursor.fetchone()
    return (max_lat, max_lon, min_lat, min_lon)

def get_scale(min_lon, max_lon, min_lat, max_lat, imgWidth, imgHeight, imgPadding):
    return min( (imgWidth - imgPadding * 2) / (max_lon - min_lon),
                 (imgHeight - imgPadding * 2) / (max_lat - min_lat))

def render_as_points(db, ctx, args):
    logging.debug('Image type is points.')

    where_clause = get_where_clause(args)
    cursor = db.cursor()
    max_lat, max_lon, min_lat, min_lon = get_extreme_coordinates(cursor, where_clause)
    scale = get_scale(min_lon, max_lon, min_lat, max_lat, args.width, args.height, args.padding)
   
    # Get points
    cursor.execute('select lat, lon, track from track_points ' + where_clause + ' order by track, id')
    row = cursor.fetchone()
    while row is not None:
        row = cursor.fetchone()

if __name__ == '__main__':
    # Init application.
    logging.basicConfig(level=logging.DEBUG)
    args = get_arguments()
    db = create_db(args.db, args.db_schema)
    if args.type == IMAGE_TYPE_OLD:
        old_algo(db, args)
    else:
        # Init drawing objects.
        surface = cairo.SVGSurface(args.output, args.width, args.height)
        ctx = cairo.Context(surface)
        
        # Fill background.
        ctx.set_source_rgb(0, 0, 0)
        ctx.paint()
        
        types = {IMAGE_TYPE_POINTS: render_as_points}
        types[args.type](db, ctx, args)
        
        logging.info('Rendering completed.')
        surface.finish()
        args.output.close() 
        logging.debug('Output closed.')
