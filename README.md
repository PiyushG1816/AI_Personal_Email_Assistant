# AI-Powered Email Assistant

A background email pipeline that fetches unread Gmail emails, enriches them with AI using LangChain + Gemini, stores results in MySQL, sends Slack alerts for meetings and high-priority emails, and creates Gmail drafts for replies.

---

## Architecture

```
Gmail API
    ↓
fetch_latest_unread()        # one unread email per tick
    ↓
parse_message()              # extract headers, body, attachments
    ↓
enrichment_chain             # RunnableParallel — 4 concurrent LLM calls
    ├── summarizer_chain     → 2-3 sentence summary
    ├── classifier_chain     → Finance / Travel / Meetings / Support / Personal / Spam / General
    ├── extract_chain        → EmailKeyInfo (dates, amounts, action, deadline, meeting details)
    └── priority_chain       → High / Mid / Low
    ↓
RunnableBranch
    ├── meeting detected     → Slack alert (manual scheduling decision)
    ├── High priority        → Gmail draft created + Slack alert
    └── everything else      → store only
    ↓
MySQL (emails table)
```

---

## Stack

| Layer | Tool |
|---|---|
| LLM | Gemini 2.0 Flash via `langchain-google-genai` |
| Orchestration | LangChain `RunnableParallel` |
| Email fetch | Gmail API (`google-api-python-client`) |
| Draft creation | LangChain `GmailCreateDraft` toolkit |
| Structured output | Pydantic `EmailKeyInfo` via `with_structured_output` |
| Database | MySQL via `mysql-connector-python` |
| Alerts | Slack Bot API |
| Scheduling | `schedule` library (every 5 minutes) |

---

## Project Structure

```
src/
├── Controller/
│   └── email_pipeline.py       ← main entry point
├── Database/
│   └── Email_storage.py        ← fetch, parse, store emails
├── services/
│   ├── Gmail_services.py       ← OAuth2 auth (runs once)
│   ├── Slack_services.py       ← send_meeting_alert, send_priority_alert
│   ├── Reply_services.py       ← LLM reply draft + GmailCreateDraft
│   └── Calender_services.py    ← calendar_node (wired in future)
└── Utils/
    └── Enrichment_chain.py     ← RunnableParallel + EmailKeyInfo schema
CLAUDE.md                       ← project context for Claude Code
```

---

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/PiyushG1816/AI-Powered-Email-Assistant.git
cd AI-Powered-Email-Assistant
```

### 2. Create and Activate Virtual Environment

```bash
python -m venv 1env
1env\Scripts\activate      # Windows
```

### 3. Install Dependencies

```bash
pip install -r Requirements.txt
```

### 4. Gmail API Credentials

- Go to https://console.cloud.google.com/
- Create a project and enable **Gmail API** and **Google Calendar API**
- Configure OAuth2 consent screen with these scopes:
  - `gmail.readonly`
  - `gmail.send`
  - `gmail.modify`
  - `gmail.labels`
  - `calendar.events`
- Download `credentials.json` and place it in the project root
- Run auth once to generate `token.pickle`:

```bash
python src/services/Gmail_services.py
```

### 5. Environment Variables

Create a `.env` file in the project root:

```env
GOOGLE_API_KEY=your_gemini_api_key
SLACK_TOKEN=xoxb-your-slack-bot-token
SLACK_CHANNEL=#general
```

### 6. MySQL Setup

Create the database and table:

```sql
CREATE DATABASE Email_assistant;

USE Email_assistant;

CREATE TABLE emails (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message_id VARCHAR(255) UNIQUE,
    sender VARCHAR(255),
    recipient VARCHAR(255),
    subject VARCHAR(500),
    timestamp DATETIME,
    body TEXT,
    has_attachment VARCHAR(3),
    thread_id VARCHAR(255),
    summary TEXT,
    priority VARCHAR(10),
    category VARCHAR(50),
    key_info JSON
);
```

---

## Running the Pipeline

```bash
python -m src.Controller.email_pipeline
```

The pipeline will:
1. Authenticate Gmail
2. Fetch the latest unread email
3. Run all 4 enrichment chains concurrently
4. Route based on meeting detection or priority
5. Store enriched email in MySQL
6. Repeat every 5 minutes

---

## Conditional Routing Logic

| Condition | Action |
|---|---|
| `meeting_title` is not None | Slack alert sent with meeting details |
| `priority == "high"` AND `action_required` is not empty | Gmail draft created + Slack alert |
| Everything else | Store in MySQL only |

---

## EmailKeyInfo Schema

Structured output enforced via Pydantic + `with_structured_output`:

```python
class EmailKeyInfo(BaseModel):
    dates: list[str]                  # any dates mentioned
    amounts: list[str]                # monetary amounts
    action_required: str              # action needed from recipient
    deadline: str | None             # deadline if mentioned
    meeting_title: str | None        # populated only for meeting emails
    meeting_date: str | None         # YYYY-MM-DD
    meeting_time: str | None         # HH:MM
    meeting_duration_minutes: int | None
```

---

## Troubleshooting

| Error | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'src'` | Run from project root using `python -m src.Controller.email_pipeline` |
| `token.pickle not found` | Run `python src/services/Gmail_services.py` to authenticate |
| `Failed to send Slack message` | Check `SLACK_TOKEN` in `.env` |
| Gemini returns wrong structure | Already handled — `with_structured_output` enforces `EmailKeyInfo` schema |
| `pickle.UnpicklingError` | Delete `token.pickle` and re-authenticate |

---

## Planned Features

- Slack Yes/No flow for manual calendar scheduling
- Multi-email processing per tick with `historyId` incremental sync
- Web UI dashboard for email summaries and routing decisions
- RAG layer to query stored emails conversationally