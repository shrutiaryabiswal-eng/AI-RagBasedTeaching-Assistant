# Converts the videos to mp3

import os
import subprocess

files = os.listdir("video")
print(files)

os.makedirs("audios", exist_ok=True)

for file in files:
    print(file)

    file_name = os.path.splitext(file)[0]

    print(file_name)

    subprocess.run([
        "ffmpeg",
        "-i",
        f"video/{file}",
        f"audios/{file_name}.mp3"
    ])