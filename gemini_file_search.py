from google import genai
from google.genai import types
import os
import time
import tempfile
from dotenv import load_dotenv
from pypdf import PdfReader, PdfWriter

load_dotenv()

# Increase timeout (5 minutes - max before server timeout)
client = genai.Client(
    api_key=os.getenv("Google_API_KEY"),
    http_options=types.HttpOptions(
        timeout=300000,  # 300 seconds (5 minutes)
    ),
)

MAX_SIZE_MB = 20  # Smaller chunks = faster query response

# Supported file types and their MIME types
SUPPORTED_MIME_TYPES = {
    # Documents
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".json": "application/json",
    ".csv": "text/csv",
    # Images
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    # Video
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".mpeg": "video/mpeg",
    ".mpg": "video/mpeg",
    ".webm": "video/webm",
    ".wmv": "video/wmv",
    ".flv": "video/x-flv",
    ".3gpp": "video/3gpp",
    ".3gp": "video/3gpp",
    # Audio
    ".mp3": "audio/mp3",
    ".wav": "audio/wav",
    ".aac": "audio/aac",
    ".flac": "audio/flac",
    ".opus": "audio/opus",
    ".m4a": "audio/m4a",
    ".ogg": "audio/ogg",
}


def get_mime_type(file_path):
    """Get MIME type from file extension."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_MIME_TYPES:
        raise ValueError(f"Unsupported file type: {ext}")
    return SUPPORTED_MIME_TYPES[ext]


def is_pdf(file_path):
    """Check if file is a PDF."""
    return os.path.splitext(file_path)[1].lower() == ".pdf"


# --- STEP 1: Split PDF by actual file size ---
def split_pdf(file_path):
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    print(f"File size: {file_size_mb:.1f} MB")

    # If file is small enough, return as-is
    if file_size_mb <= MAX_SIZE_MB:
        print("No splitting needed")
        return [file_path]

    print(f"Splitting (keeping each chunk under {MAX_SIZE_MB}MB)...")

    reader = PdfReader(file_path)
    total_pages = len(reader.pages)
    print(f"Total pages: {total_pages}")

    chunks = []
    temp_dir = tempfile.mkdtemp()

    current_writer = PdfWriter()
    chunk_start_page = 1

    for i in range(total_pages):
        # Add page to current chunk
        current_writer.add_page(reader.pages[i])

        # Save to temp file and check size
        temp_path = os.path.join(temp_dir, "temp_check.pdf")
        with open(temp_path, "wb") as f:
            current_writer.write(f)

        current_size_mb = os.path.getsize(temp_path) / (1024 * 1024)

        # If chunk exceeds limit
        if current_size_mb >= MAX_SIZE_MB:
            # If only 1 page and already too big, keep it (can't split further)
            if len(current_writer.pages) == 1:
                print(
                    f"  Warning: Page {i + 1} alone is {current_size_mb:.1f}MB (exceeds limit)"
                )
                chunk_path = os.path.join(temp_dir, f"chunk_{len(chunks) + 1}.pdf")
                os.rename(temp_path, chunk_path)
                chunks.append(chunk_path)
                print(f"  Chunk {len(chunks)}: page {i + 1} ({current_size_mb:.1f}MB)")

                current_writer = PdfWriter()
                chunk_start_page = i + 2
            else:
                # Remove last page, save chunk
                save_writer = PdfWriter()
                for j in range(len(current_writer.pages) - 1):
                    save_writer.add_page(current_writer.pages[j])

                chunk_path = os.path.join(temp_dir, f"chunk_{len(chunks) + 1}.pdf")
                with open(chunk_path, "wb") as f:
                    save_writer.write(f)

                chunk_size = os.path.getsize(chunk_path) / (1024 * 1024)
                chunks.append(chunk_path)
                print(
                    f"  Chunk {len(chunks)}: pages {chunk_start_page}-{i} ({chunk_size:.1f}MB)"
                )

                # Start new chunk with current page
                current_writer = PdfWriter()
                current_writer.add_page(reader.pages[i])
                chunk_start_page = i + 1

    # Save remaining pages
    if len(current_writer.pages) > 0:
        chunk_path = os.path.join(temp_dir, f"chunk_{len(chunks) + 1}.pdf")
        with open(chunk_path, "wb") as f:
            current_writer.write(f)

        chunk_size = os.path.getsize(chunk_path) / (1024 * 1024)
        chunks.append(chunk_path)
        print(
            f"  Chunk {len(chunks)}: pages {chunk_start_page}-{total_pages} ({chunk_size:.1f}MB)"
        )

    return chunks


# --- STEP 2: Upload files to Gemini ---
def upload_files(file_paths, mime_type):
    uploaded = []

    for i, path in enumerate(file_paths):
        size_mb = os.path.getsize(path) / (1024 * 1024)
        print(f"Uploading chunk {i + 1}/{len(file_paths)} ({size_mb:.1f}MB)...")

        file = client.files.upload(
            file=path,
            config=types.UploadFileConfig(mime_type=mime_type),
        )

        # Wait for processing
        while file.state == "PROCESSING":
            time.sleep(3)
            file = client.files.get(name=file.name)

        if file.state == "FAILED":
            raise Exception(f"Failed to process: {path}")

        uploaded.append(file)

    return uploaded


# --- STEP 3: Ask question ---
def ask(uploaded_files, mime_type, question):
    contents = []

    for f in uploaded_files:
        contents.append(
            types.Part.from_uri(file_uri=f.uri, mime_type=mime_type)
        )

    contents.append(question)

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite", contents=contents
    )

    return response.text


# --- MAIN ---
file_path = input("File path: ") or "Pdfs/WCSS.pdf"

if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
    exit()

# Get MIME type
try:
    mime_type = get_mime_type(file_path)
    print(f"File type: {mime_type}")
except ValueError as e:
    print(e)
    exit()

# Split only if PDF, otherwise use as-is
if is_pdf(file_path):
    chunks = split_pdf(file_path)
else:
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    print(f"File size: {file_size_mb:.1f} MB")
    chunks = [file_path]

print(f"\nTotal chunks: {len(chunks)}")

# Upload
uploaded_files = upload_files(chunks, mime_type)
print("Ready!\n")

# Q&A loop
while True:
    question = input("You: ")
    if question.lower() == "e":
        break

    answer = ask(uploaded_files, mime_type, question)
    print(f"Gemini: {answer}\n")

print("Done!")
