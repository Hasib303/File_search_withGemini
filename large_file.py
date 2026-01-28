
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
import time

load_dotenv()

client = genai.Client(api_key=os.getenv("Google_API_KEY"))

def process_large_file(file_path: str, system_prompt: str, user_prompt: str):

    uploaded = client.files.upload(file=file_path)

    while uploaded.state == "PROCESSING":
        time.sleep(5)
        uploaded = client.files.get(name=uploaded.name)
    
    if uploaded.state == "FAILED":
        raise Exception("File processing failed")
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=system_prompt
        ),
        contents=[
            types.Part.from_uri(file_uri=uploaded.uri, mime_type=uploaded.mime_type),
            user_prompt
        ]
    )
    
    return response.text

if __name__ == "__main__":
    
    SYSTEM_PROMPT = """
    You are a document analysis expert. 
    Extract key information accurately and format output clearly.
    Be thorough but concise.
    """
    
    USER_PROMPT = """
    Analyze this file and:
    1. Summarize the main content
    2. List key points
    3. Identify any issues or concerns
    """
    
    FILE_PATH = "Pdfs/WCSS.pdf"  # Can be video, audio, PDF, etc. up to 2GB
    
    result = process_large_file(FILE_PATH, SYSTEM_PROMPT, USER_PROMPT)
    print(result)