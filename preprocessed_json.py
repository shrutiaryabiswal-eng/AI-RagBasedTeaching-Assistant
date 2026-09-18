import requests
import os
import json
import pandas as pd
import joblib
import time


def create_embedding(text_list, retries=3):

    for attempt in range(retries):

        try:
            r = requests.post(
                "http://localhost:11434/api/embed",
                json={
                    "model": "bge-m3",
                    "input": text_list
                },
                timeout=300
            )

            print("Status Code:", r.status_code)

            r.raise_for_status()

            data = r.json()

            if "embeddings" not in data:
                raise Exception(f"Unexpected response: {data}")

            return data["embeddings"]

        except Exception as e:

            print("Embedding error:", e)

            if attempt < retries - 1:
                print("Retrying...")
                time.sleep(5)
            else:
                raise


json_folder = "jsons"

json_files = sorted(
    [f for f in os.listdir(json_folder) if f.endswith(".json")]
)

print("\nJSON files found:")
for f in json_files:
    print(f)

my_dict = []
chunk_id = 0

for video_number, json_file in enumerate(json_files, start=1):

    file_path = os.path.join(json_folder, json_file)

    print("\n====================================")
    print("Processing video:", video_number)
    print("File:", json_file)
    print("====================================")

    with open(file_path, "r", encoding="utf-8") as f:
        content = json.load(f)

    texts = [c["text"] for c in content["chunks"]]

    embeddings = []

    # Process embeddings in small batches
    batch_size = 10

    for start in range(0, len(texts), batch_size):

        batch = texts[start:start + batch_size]

        print(
            f"Embedding chunks {start} to "
            f"{start + len(batch) - 1}"
        )

        batch_embeddings = create_embedding(batch)

        embeddings.extend(batch_embeddings)

    # Store chunks
    for i, chunk in enumerate(content["chunks"]):

        chunk["chunk_id"] = chunk_id

        chunk["embedding"] = embeddings[i]

        # VIDEO NUMBER
        chunk["video_number"] = video_number

        chunk_id += 1

        my_dict.append(chunk)


# Create DataFrame
df = pd.DataFrame.from_records(my_dict)


print("FINAL DATASET")


print(df["title"].value_counts())

print("\nTotal chunks:", len(df))
print("Total videos:", df["title"].nunique())


# Save
joblib.dump(df, "embeddings.joblib")

print("\nembeddings.joblib created successfully!")