#!/usr/bin/python
"""
Generates and uploads youtube music videos one album at a time with cover art.
Up the punx. See README for help.
"""

__author__ = 'Daniel da Silva <daniel@meltingwax.net>'

import sys

if sys.version_info[:2] < (2, 7) or sys.version_info[0] != 2:
    print "Requires at least Python 2.7 (but not 3.x)."
    sys.exit(1)

import argparse
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

def sort_key_fn(song_path):
    tags = ID3.ID3(song_path)
    
    try:
        return int(tags['Track'])
    except:
        try:
            return int(tags['TRACKNUMBER'])
        except:
            return -1
    
def main():
    parser = argparse.ArgumentParser(description=sys.modules[__name__].__doc__)
    parser.add_argument('developer_key', metavar='YoutubeDeveloperKey', help='YouTube developer key')
    parser.add_argument('cover_file', metavar='CoverFile', type=file, help='Cover image file')
    parser.add_argument('song_files', metavar='SongFile', type=file, nargs='+', help='Song Files')
    parser.add_argument('--desc', dest='desc', metavar='Description', help='Youtube description for the videos')
    parser.add_argument('--email', dest='email', metavar='Email', help='YouTube email login')
    parser.add_argument('--pass', dest='pass_', metavar='Password', help='YouTube password')
    parser.add_argument('-X', '--high-quality', dest='high_quality', action='store_true',
                        help='Render videos in higher quality (slower & longer upload, but better image quality)')

    try:
        args = parser.parse_args()
    except IOError as exc:
        # We print the exception object and it will display a message like:
        # [Errno 2] No such file or directory: 'cover.jpg'        
        print exc
        return    

    if not args.cover_file.name.lower().endswith(('.jpg', '.png', '.gif')):
        print 'Image file does not exist, or is invalid'
        return

    # Login to Youtube.
    youtube_service = gdata.youtube.service.YouTubeService()
    youtube_service.email = args.email if args.email else raw_input('Email: ')
    youtube_service.password = args.pass_ if args.pass_ else getpass.getpass('Password: ')
    youtube_service.source = 'youtubegen'
    youtube_service.developer_key = args.developer_key
    youtube_service.ProgrammaticLogin()

    # Get description variable from command line, or prompt now.
    if args.desc is None:
        print 'Enter description (two blank lines to break):'
        description = ''    
        while True:
            description += raw_input() + '\n'
            if description.endswith('\n\n\n'):
                break
    else:
        description = args.desc.replace('\\n', '\n')
    
    # Generate Temporary Directory
    tmp_dir = os.path.join(tempfile.gettempdir(), 'youtubegen-%d' % int(time.time()))
    os.mkdir(tmp_dir)

    # Generate list of songs sorted by their track number. This requires first
    # converting all songs to mp3s to allow reading their track number ID3 tag.
    sorted_songs = []

    for song_file in args.song_files:
        song_path = os.path.abspath(song_file.name)

        if not os.path.exists(song_path):
            continue

        if song_path.endswith('.mp3'):
            old_song_path = song_path
            new_song_path = os.path.join(tmp_dir, os.path.basename(song_path))
            shutil.copy(old_song_path, new_song_path)
        else:
            print 'Converting', song_path, '...',
            sys.stdout.flush()
            old_song_path = song_path
            new_song_path = os.path.join(tmp_dir, os.path.splitext(os.path.basename(song_path))[0] + '.mp3')
            commands.getoutput('sox "%s" "%s"' % (old_song_path, new_song_path))
            print

        sorted_songs.append(new_song_path)

    sorted_songs.sort(key=sort_key_fn, reverse=True)    
    print 

    # Generate videos for each song and upload the videos
    cover_file_path = os.path.abspath(args.cover_file.name)

    orig_dir = os.getcwd()
    os.chdir(tmp_dir)

    for num, song_path in enumerate(sorted_songs):
        print '[%d/%d]' % (num + 1, len(sorted_songs)),
        sys.stdout.flush()

        # Write Recipe and Generate Video ---------------------------------------------
        print 'Generating...',
        sys.stdout.flush()

        mad_file = mad.MadFile(song_path)
        song_length = mad_file.total_time() / 1000
 
        recipe = os.path.join(tmp_dir, '%d.txt' % (num + 1))
        fh = open(recipe, 'w')
        fh.write('%s:1\n' % song_path)
        fh.write('%s:%d\n' % (cover_file_path, song_length))
        fh.close()

        if args.high_quality:            
            # The -mp2 causes the audio to be encoded into MP3, as opposed to
            # the default AC3. We do this because a bug appeared in Ubuntu
            # where ffmpeg would pass invalid pointers to free() from the AC3
            # functions, crash everything, and prevent the video from being made.
            command = 'dvd-slideshow -mp2 %s' % recipe 
            video_fname = '%d.vob' % (num + 1)
        else:
            command = 'dvd-slideshow -flv %s' % recipe
            video_fname = '%d.flv' % (num + 1)
            
        output = commands.getoutput(command)

        if not os.path.exists(video_fname):
            print '(failed)'
            print output
            continue
        
        # Upload To Youtube ---------------------------------------------------
        print 'Uploading...',
        sys.stdout.flush()

        id3 = ID3.ID3(song_path)

        if id3.has_key('ARTIST') and id3.has_key('TITLE'):
            title = '%s - %s' % (id3['ARTIST'], id3['TITLE'])
        else:
            title = os.path.basename(song_path).replace('.mp3', '')
        
        media_group = gdata.media.Group(
            title=gdata.media.Title(text=title),
            description=gdata.media.Description(description_type='plain',
                                                text=description),
            category=[gdata.media.Category(text='Music',
                                           scheme='http://gdata.youtube.com/schemas/2007/categories.cat',
                                           label='Music')],
            player=None)
        
        video_entry = gdata.youtube.YouTubeVideoEntry(media=media_group)
        
        youtube_service.InsertVideoEntry(video_entry, video_fname)

        # Send Newline ------------------------------------------------
        print

    print 'Temporary directory was', tmp_dir
    os.chdir(orig_dir)

if __name__ == '__main__':
    main()


