# Local Echo Scan – Web UI

A clean, responsive React user interface for **Local Echo Scan**, built with Vite and vanilla CSS. All analysis is performed through the local FastAPI backend with zero cloud dependencies.

## Prerequisites
- Node.js (v18+)
- Local Echo Scan backend running on `http://localhost:8000`

## Getting Started

1. **Install dependencies:**
   ```bash
   cd frontend
   npm install
   ```

2. **Start the development server:**
   ```bash
   npm run dev
   ```
   The UI will be available at `http://localhost:5173`.

3. **Build for production:**
   ```bash
   npm run build
   ```

## Features
- **Multi-file drag & drop** for student submissions (`.pdf`, `.docx`, `.txt`, and code files)
- **Optional lab manual upload** to strip template text
- **Adjustable sliders** for paragraph match threshold (default 80%) and pair flag threshold (default 85%)
- **Local Gemma explanations** toggle (powered by Ollama `gemma3`)
- **Copy Rings detection** highlighting student clusters ($\ge 3$ members)
- **Side-by-side passage viewer** with matching text highlighting
- **Collapsible boilerplate panel** showing all ignored template paragraphs
- **Evidence-focused design**: neutral wording, highlighting that flags are for instructor review, not automatic verdicts
