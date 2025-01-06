# Installation

First, put both files in an empty folder and make sure ffmpeg is installed. 

Now create a "media" folder where your tracks in .mp3 format will be located.

Next, configure the files:

server.py

Replace `AUTH_USERNAME` and `AUTH_PASSWORD` with your own

Also, in the 95th line, replace the port with your own if 25565 is not suitable.

main.py

Set `AUTH_USERNAME` and `AUTH_PASSWORD` to the one that server.py

Also insert your `AIOGRAM_TOKEN` and get the chat ID that will be used for management and enter in the `CHAT_ID`

Next, in line 155, replace "yourIP" with your ip (Get it through the browser). In theory, you can enter `localhost`, but sometimes it causes errors :/

And, change the port 25565 if you changed it.

# Usage
FIRST you launch server.py , after main.py

The requirement for the songs
is to have the following entries in the ID3 tags:
TIT2, TPE1, TALB and the album cover in jpg format (Or png, other formats are likely to cause errors)

To listen, go to http://yourIP:25565/stream (change the port 25565 if you changed it.)

Commands for telegram control:

/PLAY - If playback has been stopped, it continues. If you enter a number after the command, it counts it as an ID and switches to the corresponding song (ID is the sequence number of the song in the folder starting from 0)

/UPDATE - Updates the list of songs if you enter the path or folder name after it (the path or names should not contain spaces, and if you enter the folder name, the folder should be in media), then it will scan this folder specifically and use it from now on

/STOP - Stops playback. It also "resets" the song counter.

/PAUSE - Stops playback

/NEXT - Skip song

/SHUFFLE - Shuffles the list of songs
