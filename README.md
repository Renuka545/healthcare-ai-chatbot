##  Quickstart & Setup Instructions

### Prerequisites
- Python 3.10 or higher
- pip package manager

### 1. Clone & Navigate to Project Directory
```bash
git clone <repository_url>
cd healthcare_ai_chatbot
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Set Optional Gemini API Key (Optional)
The system includes an offline smart semantic emulator, but you can also attach a Google Gemini API key:
```bash
# On Windows (PowerShell):
$env:GEMINI_API_KEY="your_api_key_here"

# On Linux/macOS:
export GEMINI_API_KEY="your_api_key_here"
```

### 4. Run Evaluation Benchmark (CLI)
To run all 20 test cases and generate `evaluation_results.json`:
```bash
python evaluate.py
```

### 5. Launch the Web Application
```bash
python run.py
```
Open your browser and navigate to: **`http://127.0.0.1:8000`**

---

##  Benchmark & Test Dataset Breakdown

The test dataset (`data/evaluation_dataset.json`) covers 20 test cases across 5 categories:
- **Clear Requests**: Explicit appointment, lab result, refill, or password queries.
- **Ambiguous Requests**: Vague phrasing requiring intent disambiguation.
- **Multi-Step Requests**: Sequential or dual-action requests.
- **Sensitive Information Requests**: Queries containing SSN, credit cards, or MRNs (HIPAA privacy verification).
- **Emergency Triage Requests**: High-risk cardiac/neurological symptoms requiring immediate emergency triage.

---
