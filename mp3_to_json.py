import whisper
import json
import os

model=whisper.load_model("base")


audios=os.listdir("audios")
for audio in audios:
  print(audio)
  number=audio.split(".")[0]
  title = os.path.splitext(audio)[0]  # Remove the .mp3 extension
  print(number,title)
  result=model.transcribe(audio=f"audios/{audio}",language="hi",task="translate")
  chunks=[]
  for segment in result["segments"]:
        chunks.append({"title":title,"start": segment["start"], "end": segment["end"], "text": segment["text"]})

  chunks_with_meta_data={"chunks": chunks, "text": result["text"]}

  with open(f"jsons/{audio}.json", "w") as f:
        json.dump(chunks_with_meta_data, f)