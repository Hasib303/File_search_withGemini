from anthropic import Anthropic
import os
import tempfile
from dotenv import load_dotenv
from pypdf import PdfReader, PdfWriter

load_dotenv()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Limits
MAX_PAGES_PER_CHUNK = 99  # Claude API limit
MAX_CHUNK_SIZE_MB = 30  # Stay under 32MB processing limit


def get_pdf_info(pdf_path: str) -> tuple[int, float]:
    """Get page count and file size in MB."""
    reader = PdfReader(pdf_path)
    page_count = len(reader.pages)
    file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
    return page_count, file_size_mb


def calculate_optimal_chunk_size(pdf_path: str) -> int:
    """
    Calculate optimal pages per chunk based on both page limit and file size.

    Ensures each chunk:
    - Has max 100 pages (API limit)
    - Is under ~30MB (processing limit)
    """
    page_count, file_size_mb = get_pdf_info(pdf_path)

    if page_count == 0:
        return 1

    avg_mb_per_page = file_size_mb / page_count

    # Calculate max pages to stay under size limit
    if avg_mb_per_page > 0:
        pages_for_size_limit = int(MAX_CHUNK_SIZE_MB / avg_mb_per_page)
    else:
        pages_for_size_limit = MAX_PAGES_PER_CHUNK

    # Take minimum of page limit and size-based limit
    optimal = min(MAX_PAGES_PER_CHUNK, max(1, pages_for_size_limit))

    return optimal


def split_pdf(pdf_path: str, chunk_size: int = None) -> list[str]:
    """
    Split a PDF into chunks.

    Args:
        pdf_path: Path to the PDF file
        chunk_size: Pages per chunk. If None, calculates optimal size.

    Returns:
        List of file paths (temp files for chunks, original if no split needed)
    """
    if chunk_size is None:
        chunk_size = calculate_optimal_chunk_size(pdf_path)

    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)

    if total_pages <= chunk_size:
        return [pdf_path]

    chunk_paths = []
    num_chunks = (total_pages + chunk_size - 1) // chunk_size

    print(
        f"Splitting {total_pages} pages into {num_chunks} chunks of ~{chunk_size} pages each"
    )

    for chunk_idx in range(num_chunks):
        start_page = chunk_idx * chunk_size
        end_page = min(start_page + chunk_size, total_pages)

        writer = PdfWriter()
        for page_num in range(start_page, end_page):
            writer.add_page(reader.pages[page_num])

        temp_file = tempfile.NamedTemporaryFile(
            suffix=f"_part{chunk_idx + 1}.pdf", delete=False
        )
        writer.write(temp_file)
        temp_file.close()
        chunk_paths.append(temp_file.name)

        chunk_size_mb = os.path.getsize(temp_file.name) / (1024 * 1024)
        print(
            f"  Chunk {chunk_idx + 1}/{num_chunks}: pages {start_page + 1}-{end_page} ({chunk_size_mb:.1f} MB)"
        )

    return chunk_paths


def upload_chunk(chunk_path: str, part_name: str) -> str:
    """Upload a single PDF chunk and return its file_id."""
    with open(chunk_path, "rb") as f:
        uploaded = client.beta.files.upload(
            file=(f"{part_name}.pdf", f, "application/pdf"),
            betas=["files-api-2025-04-14"],
        )
    return uploaded.id


def query_single_chunk(
    file_id: str, part_name: str, question: str, part_info: str = ""
) -> str:
    """Query a single PDF chunk and return the response."""
    content = [
        {"type": "document", "source": {"type": "file", "file_id": file_id}},
        {"type": "text", "text": f"{part_info}{question}"},
    ]

    response_text = ""
    with client.beta.messages.stream(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        betas=["files-api-2025-04-14"],
        messages=[{"role": "user", "content": content}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            response_text += text

    return response_text


def query_pdf_sequential(pdf_path: str, question: str) -> str:
    """
    Query a large PDF by processing chunks sequentially.

    Each chunk is processed independently, then results are combined.
    """
    page_count, file_size_mb = get_pdf_info(pdf_path)
    print(f"PDF: {page_count} pages, {file_size_mb:.1f} MB")

    chunk_paths = split_pdf(pdf_path)
    num_chunks = len(chunk_paths)

    original_name = os.path.basename(pdf_path)
    base_name = os.path.splitext(original_name)[0]

    all_responses = []

    for idx, chunk_path in enumerate(chunk_paths):
        part_num = idx + 1

        if num_chunks > 1:
            part_name = f"{base_name} (Part {part_num} of {num_chunks})"
            part_info = (
                f"[This is Part {part_num} of {num_chunks} of a larger document]\n\n"
            )
        else:
            part_name = original_name
            part_info = ""

        print(f"\n{'=' * 60}")
        print(f"Processing: {part_name}")
        print(f"{'=' * 60}")

        # Upload chunk
        print("Uploading...")
        file_id = upload_chunk(chunk_path, part_name)

        # Query chunk
        print(f"\n--- Response for {part_name} ---\n")
        response = query_single_chunk(file_id, part_name, question, part_info)
        all_responses.append((part_name, response))

        # Cleanup temp file
        if chunk_path != pdf_path:
            os.unlink(chunk_path)

        print("\n")

    # If multiple chunks, provide a summary
    if num_chunks > 1:
        print(f"\n{'=' * 60}")
        print("AGGREGATING RESPONSES...")
        print(f"{'=' * 60}\n")

        # Build aggregation prompt
        combined_responses = "\n\n".join(
            [f"### {name}:\n{resp}" for name, resp in all_responses]
        )

        aggregation_prompt = f"""I asked the following question about a {page_count}-page document that was split into {num_chunks} parts:

**Question:** {question}

Here are the responses from each part:

{combined_responses}

Please provide a unified, comprehensive answer that combines insights from all parts. Avoid redundancy and organize the information clearly."""

        print("--- Final Combined Answer ---\n")

        final_response = ""
        with client.messages.stream(
            model="claude-sonnet-4-5",
            max_tokens=4096,
            messages=[{"role": "user", "content": aggregation_prompt}],
        ) as stream:
            for text in stream.text_stream:
                print(text, end="", flush=True)
                final_response += text

        print("\n")
        return final_response

    return all_responses[0][1] if all_responses else ""


# Backwards compatible function
def query_pdf(pdf_path: str, question: str) -> str:
    """Query a PDF with automatic handling for large files."""
    return query_pdf_sequential(pdf_path, question)


# Example usage
if __name__ == "__main__":
    PDF_PATH = "Pdfs/Building-AI-Agents-With-LLMs-RAG-And-Knowledge-Graphs.pdf"
    QUESTION = "Look at the document, and tell me the summary."

    response = query_pdf(PDF_PATH, QUESTION)
