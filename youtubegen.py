#!/usr/bin/python
"""
Whoa man, like, make youtube music videos, one album at a time, on linux!!!!
For usage, run the script with no arguments.
Up the punx. Requirements:
$ apt-get install sox libsox-fmt-all dvd-slideshow python-pymad
"""

__author__ = 'Daniel da Silva <meltingwax@gmail.com>'


import commands
import os
import shutil
import sys
import tempfile
import time

try:
    import mad
except ImportError:
    print 'Requires pymad <http://spacepants.org/src/pymad/>'
    sys.exit(1)

if not commands.getoutput('which sox'):
    print 'Requires sox <http://sox.sourceforge.net/>'
    sys.exit(1)

if not commands.getoutput('which dvd-slideshow'):
    print 'Requires dvd-slideshow <http://dvd-slideshow.sourceforge.net>'
    sys.exit(1)


def main():
    if len(sys.argv) == 1:
        print 'Usage: %s <image_file> song1 [song2 [song3] ...]' % sys.argv[0]
        return

    image = os.path.abspath(sys.argv[1])
    songs = map(os.path.abspath, sys.argv[2:])

    tmp_dir = os.path.join(tempfile.gettempdir(), 'youtubegen-%d' % int(time.time()))
    os.mkdir(tmp_dir)
    os.chdir(tmp_dir)
    print 'Temporary directory is', tmp_dir

    
    if not os.path.exists(image):
        print 'Image file does not exist'
        return

    for num, song in enumerate(songs):
        print '[%d/%d]' % (num + 1, len(songs)),
        print os.path.basename(song), '\t',

        if not os.path.exists(song):
            print  'File does not exist, skipping.'
            continue

        if song.endswith('.mp3'):
            old_song = song
            new_song = os.path.join(tmp_dir, os.path.basename(song))
            shutil.copy(song, new_song)
        else:
            print 'Converting song to mp3...', 
            sys.stdout.flush()
            old_song = song
            new_song = os.path.join(tmp_dir, os.path.splitext(os.path.basename(song))[0] + '.mp3')
            commands.getoutput('sox "%s" "%s"' % (old_song, new_song))


        mad_file = mad.MadFile(new_song)
        song_length = mad_file.total_time() / 1000

        recipe = os.path.join(tmp_dir, '%d.txt' % (num + 1))
        fh = open(recipe, 'w')
        fh.write('%s:1\n' % os.path.basename(new_song))
        fh.write('%s:%d\n' % (image, song_length))
        fh.close()
        
        print 'Generating video...'
        sys.stdout.flush()
        commands.getoutput('dvd-slideshow %s' % recipe)

    print 'Temporary directory is', tmp_dir


if __name__ == '__main__':
    main()


