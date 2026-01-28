from anthropic import Anthropic
import os
from dotenv import load_dotenv

load_dotenv()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Upload (Files API beta)
uploaded = client.beta.files.upload(
    file=("B25-6198_959-Sebastopol-Rd_Kitchen_PLN.pdf",
          open("Pdfs/B25-6198_959-Sebastopol-Rd_Kitchen_PLN (1).pdf", "rb"),
          "application/pdf"),
    betas=["files-api-2025-04-14"],
)
file_id = uploaded.id

# Stream the response
with client.beta.messages.stream(
    model="claude-sonnet-4-5",
    max_tokens=4096,
    betas=["files-api-2025-04-14"],  # keep this so the file_id works
    messages=[{
        "role": "user",
        "content": [
            {
                "type": "document", 
                "source": {
                    "type": "file", 
                    "file_id": file_id
                }
            },
            {
                "type": "text", 
                "text": "Review this plan set. List key issues, missing items, and a sheet-by-sheet summary."
            },
        ],
    }],
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)

# Optional: get the final assembled message object
final_msg = stream.get_final_message()
# print(final_msg)
