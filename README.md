# Honest Connect Email Agent (v1)

A command-line tool for generating sincere cold emails:

- **v1 Core**: Read two PDF resumes (sender & receiver), automatically extract structured information, and generate a genuine first-contact cold email (Subject + Body).
- **v1.1 New Feature**: Search and scrape receiver information from the web using just their name and field - no PDF or JSON file needed.
- Also compatible with v0 JSON input for manual debugging or adding detailed information.

## Prerequisites

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up Google Gemini API Key:
   ```bash
   export GEMINI_API_KEY=your_api_key
   # or
   export GOOGLE_API_KEY=your_api_key
   ```
   Get your API Key: https://makersuite.google.com/app/apikey

## Web Search Input (New Feature 🆕)

Simply provide the receiver's name and field, and the system will automatically search and scrape relevant information from the web:

```bash
python -m src.cli \
  --sender-pdf /path/to/sender.pdf \
  --receiver-name "Andrew Ng" \
  --receiver-field "AI research, deep learning" \
  --motivation "Why you want to reach out" \
  --ask "What you hope they can help with" \
  --goal "Request a 20-min chat to discuss their recent projects and your relevant experience"
```

The command will automatically:
1. Search for web pages about the person using search engines;
2. Scrape and extract relevant information from web pages;
3. Use Gemini model to organize information into a structured Profile;
4. Generate an email ready to paste, combining your motivation and ask.

Optional parameters:
- `--receiver-context`: Your relationship with the receiver or recent news you're following (optional).
- `--max-pages`: Maximum number of web pages to scrape, default 3.
- `--model`: Gemini model to use, default `gemini-2.0-flash`.

## PDF Input (Recommended)

```bash
python -m src.cli \
  --sender-pdf /path/to/sender.pdf \
  --receiver-pdf /path/to/receiver.pdf \
  --motivation "Why you want to reach out" \
  --ask "What you hope they can help with" \
  --goal "Request a 20-min chat to discuss their recent projects and your relevant experience"
```

The command will automatically:
1. Extract plain text from PDF using PyPDF2;
2. Use Gemini model to organize text into a structured Profile (name/education/experiences/skills/projects/raw_text);
3. Generate an email ready to paste, combining your motivation and ask.

Optional parameters:
- `--receiver-context`: Your relationship with the receiver or recent news you're following (optional).
- `--model`: Gemini model to use, default `gemini-2.0-flash`.

## JSON Input (v0 Compatible)

```bash
python -m src.cli \
  --sender-json examples/sender.json \
  --receiver-json examples/receiver.json \
  --goal "Request a 20-min chat to discuss their recent projects and your relevant experience"
```

Example files are in the `examples/` directory. Fields include `name`, `raw_text`, `motivation`, `ask`, and optionally `education`, `experiences`, `skills`, `projects`.

The generated email will be printed to the terminal, ready to copy and paste into your email client.
