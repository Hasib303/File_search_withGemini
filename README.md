# Gemini File Search

This program leverages Google's Gemini API to perform intelligent file searches and question-answering on documents. It uploads files to Gemini and allows users to interactively ask questions about the content.

## Supported Files

| Type | Extensions |
|------|------------|
| Documents | `.pdf`, `.txt`, `.json`, `.csv` |
| Images | `.png`, `.jpg`, `.jpeg`, `.webp` |
| Video | `.mp4`, `.mov`, `.mpeg`, `.mpg`, `.webm`, `.wmv`, `.flv`, `.3gp` |
| Audio | `.mp3`, `.wav`, `.aac`, `.flac`, `.opus`, `.m4a`, `.ogg` |

## Get API Key

To use this program, you need a Google API key for Gemini.

1. Go to [Google AI Studio](https://aistudio.google.com/).
2. Click on **"Get API key"**.
3. Click **"Create API key"** to generate your unique key.

## Setup

### 1. Clone the repository
```bash
git clone <repository-url>
cd <repository-directory>
```

### 2. Install dependencies
Ensure you have Python installed, then run:
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a `.env` file in the root directory and add your Google API key:
```
Google_API_KEY=your_api_key_here
```

### 4. Run the program
```bash
python gemini_file_search.py
```
