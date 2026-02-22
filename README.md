# Foundtel: The AI Chief of Staff 🤖

Foundtel is a proactive AI chief of staff that gives tech founders a 3-minute morning intelligence brief. It synthesizes data from Gmail, Stripe, and competitor sites to save you 2 hours of daily manual catch-up.

## 🚀 Key Features

- **Daily Morning Brief**: Synthesized intelligence delivered to your inbox.
- **Revenue Pulse**: Real-time Stripe MRR and revenue monitoring.
- **Inbox Priorities**: Urgent emails categorization and surfacing.
- **Competitor Radar**: Automated tracking of competitor blogs and changelogs.
- **Agent2Agent (A2A)**: High-performance multi-agent architecture.

## 🛠️ Technical Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Database**: [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) with [Beanie ODM](https://beanie-odm.dev/)
- **AI Agent**: [Google ADK](https://github.com/google/adk-python) (Agent Development Kit)
- **Deployment**: [Google Cloud Run](https://cloud.google.com/run) with automated [GitHub Actions](/.github/workflows/deploy.yml)

## 📁 Repository Structure

- `founder_agent/`: Core agent logic, sub-agents, and database models.
- `scripts/`: Utility scripts for database management and deployments.
- `templates/`: Jinja2 dashboard and authentication templates.
- `docs/`: Technical roadmap and brand strategy.
- `.github/`: CI/CD workflows for Cloud Run.

## ⚙️ Setup & Installation

1.  **Environment**: Create a `.env` file based on the technical roadmap in `docs/`.
2.  **Authentication**: Run `python scripts/gmail_auth.py` (ensure you have `credentials.json`).
3.  **Run Locally**:
    ```bash
    uvicorn app:app --reload
    ```
4.  **Local Dashboard**: Visit `http://localhost:8000`.

## 🔒 Security

- This project uses GitHub Secret Scanning. Never commit `.env` or files in `secrets/`.
- Credentials should be managed via GitHub Actions Secrets for production.

---

Built with ❤️ by [CoderRahul01](https://github.com/CoderRahul01) using [Google ADK](https://google.github.io/adk-docs/).
