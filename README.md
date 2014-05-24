    __     __      _______    _           _____            
    \ \   / /     |__   __|  | |         / ____|           
     \ \_/ /__  _   _| |_   _| |__   ___| |  __  ___ _ __  
      \   / _ \| | | | | | | | '_ \ / _ \ | |_ |/ _ \ '_ \ 
       | | (_) | |_| | | |_| | |_) |  __/ |__| |  __/ | | |
       |_|\___/ \__,_|_|\__,_|_.__/ \___|\_____|\___|_| |_|
                                                       

Author:  Daniel da Silva <var.mail.daniel@gmail.com>
License: GPL v2.0 <http://www.gnu.org/licenses/gpl-2.0.txt>


Description
===========

YoutubeGen is a script for uploading an album to invidiual youtube videos. It does not matter what format the song audio files are in, and the visual portion of the video is made into the cover art.

The videos will be named '%artist - %title' based on the ID3 tags of the MP3 file, but if they fail to exist, the filename will be used. If you specify -P (or always_playlist=yes in [Settings] under ~/.youtubegenrc), a playlist will be generated. The name of the playlist will be inferred from the first '%artist - %album' found, otherwise it will prompt you.

Install
=======

This script is made specifically for linux systems, and may work on macs, but not windows.

   $ sudo apt-get install sox libsox-fmt-all python-id3 
   $ sudo pip install youtubegen

If you are using Ubuntu, you must download FFmpeg from their site and install it over the Ubuntu version.

Developer Key
-------------

The videos produced are automatically uploaded to your youtube account. In order to do this, you must get a YouTube developer key (it's free). To do this, go to:

   http://code.google.com/apis/youtube/dashboard/gwt/index.html

Uploading an Album
==================

Suppose you have an album like this:

   $ ls
   01 - army song.mp3       06 - voice of youth.mp3  11 - banner of hope.mp3      
   02 - juvenile.mp3        07 - burn 'em down.mp3   12 - law of the jungle.mp3   
   03 - so slow.mp3         08 - urban rebel.mp3     13 - the prisoner.mp3
   04 - vicious circle.mp3  09 - jailhouse rock.mp3  14 - christianne.mp3
   05 - attack.mp3          10 - sonic omen.mp3      15 - black leather girl.mp3
   cover.jpg

To upload the whole album, run the program like this:

   $ youtubegen cover.jpg *.mp3

You will be prompted for the necessary login information, developer key, and a description for the videos. To avoid being prompted each time, set the command line flags (described in the output of ``youtubgen --help``) or create a ~/.youtubegenrc (described in ``example.youtubegenrc'').