# SentinelLab local Docker deployment (React + API + MongoDB)

This is a **full-stack developer preview**, not a production-hardened deployment. The React frontend is served by Nginx in the `web` container, proxying `/api/` to the FastAPI service. The original Emergent requirements freeze references private vendor assets; `backend/requirements.runtime.txt` is a portable subset. AI assistant functionality depends on the Emergent adapter and is not bundled in this image; other integrations may need additional dependencies.

1. Install Docker Desktop with Compose.
2. Copy `.env.example` to `.env` and set **unique, strong** `JWT_SECRET` and `ADMIN_PASSWORD`. Keep `.env` private.
3. Run `docker compose up --build -d` from the repository root.
4. Open `http://127.0.0.1:8080` for the React UI and `http://127.0.0.1:8000/docs` for API documentation. Both bind to localhost; MongoDB is not published.
5. View logs with `docker compose logs -f api` and stop with `docker compose down`. **Do not** use `down -v` unless you intend to delete stored MongoDB data.

Security: admin credentials are required and the demo analyst account is opt-in via `ENABLE_DEMO_ACCOUNTS=true`. Never enable demo credentials on an exposed service. Login sets a Secure cookie; for localhost HTTP, prefer the returned Bearer token for API testing. Deploy behind HTTPS before browser cookie-based usage. The backend currently has permissive signup and other features still awaiting security review; do not expose publicly.

Validation: GitHub CI includes container build/startup, frontend/API routing, authentication, and authorization smoke checks. Browser-level end-to-end UI validation and third-party AI adapter portability remain pending. See [Engineering Journey](ENGINEERING_JOURNEY.md) for milestones, failures, and CI evidence.
