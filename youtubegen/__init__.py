#!/usr/bin/python
"""
Generates and uploads youtube music videos one album at a time with cover art.
Uses FFmpeg at the core. See README for help and options.
"""

# TODO:
# - When converting cover files, place the converted image the temporary
#   directory. Do not affect the existing file.
# - Use commands.getstatusoutput(cmd) in place of commands.getoutput()
#   and check error code as an addition way to fail.

__author__ = 'Daniel da Silva <var.mail.daniel@gmail.com>'

import sys

if sys.version_info[:2] < (2, 7) or sys.version_info[0] != 2:
    print "Requires at least Python 2.7 (but not 3.x)."
    sys.exit(1)

import argparse
import commands
import ConfigParser
import getpass
import os
import pipes
import shutil
import sys
import tempfile
import time


try:
    import ID3
except ImportError:
    raise ImportError, 'Requires ID3 module <http://id3-py.sourceforge.net/>'

try:
    import Image
except ImportError:
    raise ImportError, 'Requires Pillow <https://pypi.python.org/pypi/Pillow/>'

try:
    import gdata.youtube.service
except ImportError:
    raise ImportError, 'Requires gdata module <https://developers.google.com/gdata/articles/python_client_lib>'

if not commands.getoutput('which sox'):
    raise ImportError, 'Requires sox <http://sox.sourceforge.net/>'

if not commands.getoutput('which ffmpeg'):
    raise ImportError, 'Requires FFmpeg <http://www.ffmpeg.org>'


class Bunch(dict):
    """A dictionary with dot access. Attribute access on missing key results
    in None."""
    def __setattr__(self, name, value):
        self[name] = value
        self.__dict__[name] = value

    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            return None


def sort_key_fn(song_path):
    tags = ID3.ID3(song_path)
    
    try:
        return int(tags['Track'])
    except:
        try:
            return int(tags['TRACKNUMBER'])
        except:
            return -1

def get_video_title(song_path):
    tags = ID3.ID3(song_path)

    if tags.artist and tags.title:
        title = '%s - %s' % (tags.artist, tags.title)
    else:
        title = os.path.basename(song_path).replace('.mp3', '')

    title = title.decode('utf-8', 'ignore')  # drop bad UTF-8 characters
    
    return title


def main():
    parser = argparse.ArgumentParser(description=sys.modules[__name__].__doc__)

    parser.add_argument('cover_file', metavar='CoverFile', type=file,
                        help='Cover image file')
    parser.add_argument('song_files', metavar='SongFile', type=file, nargs='+',
                        help='List of song files')
    
    parser.add_argument('--email', dest='email', metavar='Email',
                        help='YouTube email login')
    parser.add_argument('--pass', dest='pass_', metavar='Password',
                        help='YouTube password')
    parser.add_argument('--dev-key', dest='developer_key', metavar='YoutubeDeveloperKey',
                        help='YouTube developer key')
    
    parser.add_argument('--desc', dest='desc', metavar='Description',
                        help='Youtube description for the videos')
    parser.add_argument('--tags', dest='keywords', metavar='Tags',
                        help='YouTube tags for the videos (ex: "punk, hardcore")')
    parser.add_argument('-P', '--playlist', dest='playlist', action='store_true',
                        help='Group all videos into a playlist')
    parser.add_argument('-X', dest='lock_uploads', action='store_true',
                        help='Lock multiple processes from simultaneously uploading')

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
    
    # ------------------------------------------------------------------------------    
    # Set up the configuration in a Bunch. Some options can only be set from the
    # config file.
    # 
    # Resolve order is:
    # 1. command line flags
    # 2. config file
    # 3. prompting the user    
    # ------------------------------------------------------------------------------
    config = Bunch()
    
    # Resolve from arguments ------------------------------------------------------
    if args.email:
        config.email = args.email
    if args.pass_:
        config.pass_ = args.pass_
    if args.developer_key:
        config.developer_key = args.developer_key
    if args.desc:
        config.desc = args.desc.replace('\\n', '\n')
    if args.keywords:
        config.keywords = args.keywords
    if args.lock_uploads:
        config.lock_uploads = args.lock_uploads
    if args.playlist:
        config.playlist = args.playlist
    
    # Resolve from config ------------------------------------------------------
    config_path = os.path.expanduser("~/.youtubegenrc")

    if os.path.exists(config_path):
        cfg = ConfigParser.ConfigParser()
        cfg.read(config_path)

        # Direct transfers of config file variables to the bunch.
        # Each item is follows: (NameInBunch, (ConfigSection, ConfigOption))
        transfer = [('email', ('Login', 'email')),
                    ('pass_', ('Login', 'pass')),
                    ('developer_key', ('Login', 'developer_key')),
                    ('keywords', ('Settings', 'keywords')),
                    ('lock_uploads', ('Settings', 'always_lock_uploads')),
                    ('playlist', ('Settings', 'always_playlist'))]
        
        for name, (section, option) in transfer:
            if (name not in config) and cfg.has_section(section) and cfg.has_option(section, option):
                config[name] = cfg.get(section, option)

        # Special transfers
        if not config.desc and cfg.has_section('Settings') and cfg.has_option('Settings', 'skip_description'):
            config.desc = '  '
    
    # Resolve from prompt ------------------------------------------------------
    if not config.email:
        config.email = raw_input('Email: ')

    if not config.pass_:
        config.pass_ = getpass.getpass('Password: ')

    if not config.developer_key:
        config.developer_key = raw_input('YouTube Developer Key: ')

    if not config.desc:
        print 'Enter description (enter two blank lines to break):'
        config.desc = ''
        
        while True:
            config.desc += raw_input() + '\n'
            if config.desc.endswith('\n\n\n'):
                break
        
        config.desc = config.desc.strip()

    # ---------------------------------------------------------------------------

    # Login to Youtube.
    youtube_service = gdata.youtube.service.YouTubeService()
    youtube_service.email = config.email
    youtube_service.password = config.pass_
    youtube_service.developer_key = config.developer_key
    youtube_service.source = 'youtubegen'
    youtube_service.ProgrammaticLogin()
    
    # Generate Temporary Directory
    tmp_dir = os.path.join(tempfile.gettempdir(), 'youtubegen-%d' % int(time.time()))
    os.mkdir(tmp_dir)

    # Convert cover file to 800x800 JPEG. FFmpeg requires the image size to
    # be Even x Even.

    cover_file_path = os.path.abspath(args.cover_file.name)

    im = Image.open(cover_file_path)

    if im.mode != "RGB":
        im = im.convert("RGB")

    im = im.resize((800, 800), Image.ANTIALIAS)

    cover_file_path = os.path.splitext(cover_file_path)[0]
    cover_file_path += ".jpg"

    im.save(cover_file_path, "JPEG")

    # Generate list of songs sorted by their track number. This requires first
    # converting all songs to mp3s to allow reading their track number ID3 tag.
    sorted_songs = []

    for song_file in args.song_files:
        song_path = os.path.abspath(song_file.name)

        if not os.path.exists(song_path):
            continue

        if song_path.lower().endswith('.mp3'):
            old_song_path = song_path
            new_song_path = os.path.join(tmp_dir, os.path.basename(song_path))
            shutil.copy(old_song_path, new_song_path)
        else:
            sys.stdout.write('Converting %s... ' % song_path)
            sys.stdout.flush()
            old_song_path = song_path
            new_song_path = os.path.join(tmp_dir, os.path.splitext(os.path.basename(song_path))[0] + '.mp3')
            commands.getoutput('sox "%s" "%s"' % (old_song_path, new_song_path))
            print

        sorted_songs.append(new_song_path)

    sorted_songs.sort(key=sort_key_fn)

    # Generate a playlist for this album --------------------------------------------------
    if config.playlist:
        playlist_name = None
        
        for song_path in sorted_songs:
            tags = ID3.ID3(song_path)
            if tags.get('ARTIST') and tags.get('ALBUM'):
                playlist_name = '%s - %s' % (tags['ARTIST'], tags['ALBUM'])
                break
        
        if playlist_name is None:
            playlist_name = raw_input('Playlist Title: ')
        
        playlist_entry = youtube_service.AddPlaylist(playlist_name, config.desc)
        if isinstance(playlist_entry, gdata.youtube.YouTubePlaylistEntry):
            print 'Created Playlist "%s"' %  playlist_name
        else:
            print 'Failed to create Playlist "%s"' % playlist_name
            playlist_entry = None
    else:
        playlist_entry = None
        sorted_songs.reverse()
    
    sys.stdout.flush()
    
    # ------------------------------------------------------------------------------
    # Main processing loop for songs
    #
    # In the body of this loop, the following actions in order:
    # 1. Generate Video File
    # 2. Upload to YouTube
    # 3. Add to PlayList (if we made one)
    # ------------------------------------------------------------------------------    
    orig_dir = os.getcwd()
    os.chdir(tmp_dir)

    for num, song_path in enumerate(sorted_songs):
        sys.stdout.write('[%d/%d] ' % (num + 1, len(sorted_songs)))
        sys.stdout.flush()
        
        # Generate Video ---------------------------------------------
        sys.stdout.write('Generating... ')
        sys.stdout.flush()
        
        video_fname = '{}.mp4'.format(num)
        command = ('ffmpeg -f image2 -loop 1 -i {} -i {} '
                   '-c:v libx264 -tune stillimage -c:a aac '
                   '-strict experimental -b:a 192k -shortest '
                   '{}').format(pipes.quote(cover_file_path),
                                pipes.quote(song_path),
                                pipes.quote(video_fname))

        output = commands.getoutput(command)
        
        if not os.path.exists(video_fname):
           sys.stdout.write('(failed)\n\n')
           sys.stdout.write(output)
           sys.stdout.flush();
           continue
        
        # Upload To Youtube ---------------------------------------------------

        # Build the metadata object (gdata.media.Group)        
        media_group = gdata.media.Group(player=None,
                                        title=gdata.media.Title(text=get_video_title(song_path)),
                                        description=gdata.media.Description(description_type='plain', text=config.desc),
                                        category=[gdata.media.Category(text='Music', label='Music')],
                                        keywords=(gdata.media.Keywords(text=config.keywords) if config.keywords else None))

        # Upload the video, only in this comment section does locking have any effect.
        video_entry = gdata.youtube.YouTubeVideoEntry(media=media_group)
        lock_fname = os.path.join(tempfile.gettempdir(), 'youtubegen-upload-lock')

        sys.stdout.write('Uploading')
        sys.stdout.flush()
        
        try:
            if config.lock_uploads:
                while os.path.exists(lock_fname):
                    time.sleep(.5)
                assert not os.path.exists(lock_fname)
                lock_file = open(lock_fname, 'w')
                lock_file.write('1')
                lock_file.close()
                assert os.path.exists(lock_fname)

            sys.stdout.write('... ')
            sys.stdout.flush()

            video_entry = youtube_service.InsertVideoEntry(video_entry, video_fname)
        finally:
            if config.lock_uploads:
                try:
                    os.remove(lock_fname)
                except:
                    pass
        
        # Add To Playlist, if we made one -------------------------
        if playlist_entry is not None:
            playlist_uri = playlist_entry.feed_link[0].href
            video_id = video_entry.id.text.split('/')[-1]
            
            playlist_video_entry = youtube_service.AddPlaylistVideoEntryToPlaylist(
                playlist_uri, video_id)
            
            if not isinstance(playlist_video_entry, gdata.youtube.YouTubePlaylistVideoEntry):
                sys.stdout.write('[Failed to add to playlist] ')
        
        # Send Newline ------------------------------------------------
        print

    print 'Temporary directory was', tmp_dir
    os.chdir(orig_dir)


if __name__ == '__main__':
    main()


