from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
import time

load_dotenv()

client = genai.Client(api_key=os.getenv("Google_API_KEY"))

# Upload file with explicit mime_type (supports up to 2GB)
uploaded_file = client.files.upload(
    file='Pdfs/WCSS.pdf',
    config={'mime_type': 'application/pdf'}
)

# Wait for processing
while uploaded_file.state == "PROCESSING":
    time.sleep(5)
    uploaded_file = client.files.get(name=uploaded_file.name)

if uploaded_file.state == "FAILED":
    raise Exception("File processing failed")

print("File ready!")

# Q&A loop
while True:
    question = input("You: ")
    if question.lower() == 'e':
        break

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            types.Part.from_uri(file_uri=uploaded_file.uri, mime_type="application/pdf"),
            question
        ]
    )
    print("Gemini:", response.text)

print("Done!")
