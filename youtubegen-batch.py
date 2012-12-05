#!/usr/bin/python
"""
Write a text file that will queue uploading multiple albums,
and then use this program to execute it.
"""

import argparse
import collections
import getpass
import os
import sys

def main():
    parser = argparse.ArgumentParser(description=sys.modules[__name__].__doc__)
    parser.add_argument('developer_key', metavar='YoutubeDeveloperKey', help='YouTube developer key')
    parser.add_argument('input_file', metavar='InputFile', type=file, help='Location of input file')
    parser.add_argument('--verify', dest='verify', action='store_true')
    
    try:
        args = parser.parse_args()
    except IOError as exc:
        print exc
        return    

    # Break into blocks
    blocks = [[1]]
    for i, line in enumerate(args.input_file):
        line = line.strip()
        if line:
            blocks[-1].append(line)
        else:
            blocks.append([i+1])
    
    blocks = filter(lambda b: len(b) > 1, blocks)
    
    # Parse each block
    AlbumUpload = collections.namedtuple('AlbumUpload', 'dir cover song_glob desc')
    albums = []

    for block in blocks:
        line_number = block.pop(0)
        
        if len(block) < 4:
            print 'Bad block at line #%d (too short)' % line_number             
            continue
        
        album = AlbumUpload(block[0], block[1], block[2], '\n'.join(block[3:]))
        albums.append(album)

    # Build and run commands
    email = raw_input('Email: ')
    pass_ = getpass.getpass('Password: ')
    print

    for album in albums:
        os.chdir(album.dir)
        command = ("youtubegen.py -X --email '%s' --pass '%s' --desc \'%s\' %s %s %s"
                   % (email, pass_, album.desc, args.developer_key, album.cover, album.song_glob))
        sys.stdout.write('>>' + command)
        sys.stdout.flush()

        if not args.verify:
            os.system(command)

    
if __name__ == '__main__':
    main()
