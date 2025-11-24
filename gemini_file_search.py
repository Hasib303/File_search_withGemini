from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
import time

load_dotenv()

client = genai.Client(api_key=os.getenv("Google_API_KEY"))

file_search_store = client.file_search_stores.create(config={'display_name': 'File search store'})

operation = client.file_search_stores.upload_to_file_search_store(
  file='Pdfs/Submittal_Set_.pdf',
  file_search_store_name=file_search_store.name,
  config={
      'display_name' : 'Submittal Set',
  }
)

while not operation.done:
    time.sleep(5)
    operation = client.operations.get(operation)

def getAns(client, file_search_store_name, question):
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=question,
        config=types.GenerateContentConfig(
            tools=[
                types.Tool(
                    file_search=types.FileSearch(
                        file_search_store_names=[file_search_store_name]
                    )
                )
            ]
        )
    )

    return response.text

while True:
    question = input("You: ")
    if question.lower() == 'e':
        break
    answer = getAns(client, file_search_store.name, question)
    print("Gemini: ", answer) 

print("Done!")