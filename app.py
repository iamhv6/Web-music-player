from flask import Flask, render_template, jsonify, request, send_from_directory
import os
import yt_dlp
import re
import requests

app = Flask(__name__)

# Directory to store downloaded songs/videos
DOWNLOAD_DIR = "songs"
if not os.path.exists(DOWNLOAD_DIR): #should create a path/folder if the folder doesnt exist
    os.makedirs(DOWNLOAD_DIR)

def sanitize_filename(filename): 
    return re.sub(r"[^\w\-]", "_", filename)

def download(ydl_opts, search_query): #the main function that will downlaod the videos from ytdl the the query is passed
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([search_query])

def extract_metadata(info): #function to get metadata of the video you are downloading, used to enchance your web ui
    
    if "entries" not in info or not info["entries"]: #meta data if ytdl doesnt find any metadata
        return {
            "title": "Unable to fetch",
            "thumbnail": "",
            "duration": 0, #value accepted here is only in integers
            "uploader": "null",
            "channel_image": "", #idk was unable to fetch
            "description": "null",
            "lyrics": "null",
        }

    description = info["entries"][0].get("description", "No description available.") #sometimes ytdl returns no description for the video but we have other metadata present for the video so we set the description with a string
    
    if any(keyword in description for keyword in ["Lyrics", "Lyrics:", "LYRICS", "LYRICS:"]): #most of the songs have lyrics in the description of the video using those by a string functions
        match = re.search(r"(?i)\bLYRICS:?\b\s*(.*)", description, re.DOTALL)
        lyrics = match.group(1).strip() if match else "No lyrics available"
        new_description = re.split(r'(?i)\bLYRICS:?\b', description, maxsplit=1)[0].strip()
    else:
        lyrics = "No lyrics available"
        new_description = description  # No split needed
    
    return {
        "title": info["entries"][0].get("title", "Unknown Title"), #incase ytdl fails to extract the title
        "thumbnail": info["entries"][0].get("thumbnail", ""),
        "duration": info["entries"][0].get("duration", 0),
        "uploader": info["entries"][0].get("uploader", "Unknown Uploader"), #incase ytdl fails to extract the uploader details
        "channel_image": "", #idk how to get the channel img 
        "description": new_description,
        "lyrics": lyrics,
    }


def download_song(song_name): #this function will download only the audio/mp3 when called
    sanitized_name = sanitize_filename(song_name)
    search_query = f"ytsearch:{song_name} audio"
    
    ydl_opts = { 
        "format": "bestaudio/best", #these parameters provide the best auido availabe for the video, it can be changed to lower a quality 
        "outtmpl": f"{DOWNLOAD_DIR}/{sanitized_name}", #loaction where the downloaded file would be located
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio", #still got no idea how ffmpeg works 
                "preferredcodec": "mp3", #change this if you want your audio file other than mp3
                "preferredquality": "192", #do not touch this
            }
        ],
    }

    # Extract metadata without downloading again
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(search_query, download=True)

    metadata = extract_metadata(info)
    metadata["filename"] = f"{sanitized_name}.mp3"

   # print("Metadata:", metadata)  # Debugging
    return metadata

def dlvideo(song_name): #function to download the video along with the audio
    sanitized_name = sanitize_filename(song_name)
    search_query = f"ytsearch:{song_name}"
    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best", # use bestvideo/best if you want to donwload only the video without the audio
        "outtmpl": f"{DOWNLOAD_DIR}/{sanitized_name}",
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(search_query, download=True)
    metadata = extract_metadata(info)
    metadata["filename"] = f"{sanitized_name}.mp4"
    print("Metadata:", metadata)  # Debugging
    return metadata

@app.route("/", methods=["GET", "POST"])
def index():
   # render_template("index.html", quote=quote, title="Song Title", uploader="Uploader Name")

    if request.method == "POST":
        song = request.form["song"]
        video_type = request.form["type"]
        #basic decision to check if the args passed are mp3 or mp4
        if video_type == "mp3":
            metadata = download_song(song)
            return render_template("player.html", type="audio", **metadata)
        elif video_type == "mp4":
            metadata = dlvideo(song)
            return render_template("player.html", type="video", **metadata)
    
    return render_template("index.html") #sends the submited data to the html file

@app.route("/get-quote") 
def get_quote(): #function that generates a random quote while the video is being downloaded
    try:
        response = requests.get("https://zenquotes.io/api/random")
        data = response.json()
        return jsonify(data) 
    except Exception as e:
        return jsonify({"error": str(e)}), 500 #usually wont throw up an error

@app.route("/songs/<filename>")  #the path where your downloaded mp3/mp4 file will be saved
def serve_file(filename):
    if filename.endswith(".mp3"):  #change the download directory if you want to save the auido/video files in different folders
        return send_from_directory(DOWNLOAD_DIR, filename, mimetype="audio/mpeg")
    elif filename.endswith(".mp4"):
        return send_from_directory(DOWNLOAD_DIR, filename, mimetype="video/mp4")
    else:
        return send_from_directory(DOWNLOAD_DIR, filename)

if __name__ == "__main__":
    app.run(debug=True) #important to run the debugger
