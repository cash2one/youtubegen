#!/usr/bin/python
"""
Whoa man, like, make youtube music videos, one album at a time, on linux!!!!
For usage, run the script with no arguments.
Up the punx. Requirements:
$ apt-get install sox libsox-fmt-all dvd-slideshow python-pymad python-id3 python-gdata
"""

__author__ = 'Daniel da Silva <meltingwax@gmail.com>'


import commands
import getpass
import os
import shutil
import sys
import tempfile
import time

try:
    import ID3
except ImportError:
    print 'Requires ID3 module <http://id3-py.sourceforge.net/>'
    sys.exit(1)

try:
    import gdata.youtube.service
except ImportError:
    print 'Requires gdata module <https://developers.google.com/gdata/articles/python_client_lib>'
    sys.exit(1)

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
        print 'Usage: %s <youtube_developer_key> <image_file> song1 [song2 [song3] ...]' % sys.argv[0]
        return

    developer_key = sys.argv[1]
    image = os.path.abspath(sys.argv[2])
    songs = map(os.path.abspath, sys.argv[3:])

    if not os.path.exists(image):
        print 'Image file does not exist'
        return

    # Login to Youtube.
    youtube_service = gdata.youtube.service.YouTubeService()
    youtube_service.email = raw_input('Email: ')
    youtube_service.password = getpass.getpass('Password: ')
    youtube_service.source = 'youtubegen'
    youtube_service.developer_key = developer_key
    youtube_service.ProgrammaticLogin()    

    # Ask user for description
    description = ''

    print 'Enter description (two blank lines to break):'
    
    while True:
        description += raw_input() + '\n'

        if description.endswith('\n\n\n'):
            break
    
    # Generate Temporary Directory
    tmp_dir = os.path.join(tempfile.gettempdir(), 'youtubegen-%d' % int(time.time()))
    os.mkdir(tmp_dir)
    orig_dir = os.getcwd()
    os.chdir(tmp_dir)

    # Generate list of songs sorted by their track number. This requires first
    # converting all songs to mp3s to allow reading their track number ID3 tag.
    sorted_songs = []

    for song in songs:
        if not os.path.exists(song):
            continue

        if song.endswith('.mp3'):
            old_song = song
            new_song = os.path.join(tmp_dir, os.path.basename(song))
            shutil.copy(song, new_song)
        else:
            print 'Converting', song, '...',
            sys.stdout.flush()
            old_song = song
            new_song = os.path.join(tmp_dir, os.path.splitext(os.path.basename(song))[0] + '.mp3')
            commands.getoutput('sox "%s" "%s"' % (old_song, new_song))
            print

        sorted_songs.append(new_song)

    sorted_songs = sorted(sorted_songs, key=lambda f: ID3.ID3(f).get('TRACKNUMBER', 0))
    sorted_songs.reverse()

    print

    # Generate videos for each song and upload the videos
    for num, song in enumerate(sorted_songs):
        print '[%d/%d]' % (num + 1, len(songs)),
        sys.stdout.flush()

        # Generate Video ------------------------
        print 'Generating...',
        sys.stdout.flush()

        mad_file = mad.MadFile(new_song)
        song_length = mad_file.total_time() / 1000
 
        recipe = os.path.join(tmp_dir, '%d.txt' % (num + 1))
        fh = open(recipe, 'w')
        fh.write('%s:1\n' % os.path.basename(new_song))
        fh.write('%s:%d\n' % (image, song_length))
        fh.close()

        commands.getoutput('dvd-slideshow %s' % recipe)

        if not os.path.exists('%d.vob' % (num + 1)):
            print '(failed)'
            continue
        
        # Upload To Youtube ----------------------
        print 'Uploading...',
        sys.stdout.flush()

        id3 = ID3.ID3(song)

        if id3.has_key('ARTIST') and id3.has_key('TITLE'):
            title = '%s - %s' % (id3['ARTIST'], id3['TITLE'])
        else:
            title = os.path.basename(song).replace('.mp3', '')

        media_group = gdata.media.Group(
            title=gdata.media.Title(text=title),
            description=gdata.media.Description(description_type='plain',
                                                text=description),
            category=[gdata.media.Category(text='Music',
                                           scheme='http://gdata.youtube.com/schemas/2007/categories.cat',
                                           label='Music')],
            player=None)
        
        video_entry = gdata.youtube.YouTubeVideoEntry(media=media_group)
        
        youtube_service.InsertVideoEntry(video_entry, '%d.vob' % (num + 1))

        # Send Newline ---------------------------
        print

    print 'Temporary directory was', tmp_dir
    os.chdir(orig_dir)

if __name__ == '__main__':
    main()


