# ⛓️🌙 MOONSHITDEV 🌙⛓️

> Experimental playground for APIs, dashboards, automation scripts, and modular system services.
> Built fast, extended faster. No bloat, just code.

```
███╗   ███╗ ██████╗  ██████╗ ███╗   ██╗███████╗██╗  ██╗██╗████████╗
████╗ ████║██╔═══██╗██╔═══██╗████╗  ██║██╔════╝██║  ██║██║╚══██╔══╝
██╔████╔██║██║   ██║██║   ██║██╔██╗ ██║███████╗███████║██║   ██║   
██║╚██╔╝██║██║   ██║██║   ██║██║╚██╗██║╚════██║██╔══██║██║   ██║   
██║ ╚═╝ ██║╚██████╔╝╚██████╔╝██║ ╚████║███████║██║  ██║██║   ██║   
╚═╝     ╚═╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝╚═╝   ╚═╝   
```

## 🚀 Features

- FastAPI + Uvicorn backend
- Node.js scripts for scraping and automation
- Systemd services & timers for deployment
- File API with upload/download dashboard
- Reddit Dashboard with mod tools and multi-user switching
- Domain tools (Cloudflare price scrapers, TLD explorers)
- Easy plug-and-play endpoints

## 🛠️ Stack

- Python (FastAPI, Uvicorn)
- Node.js
- Nginx + Let’s Encrypt
- Linux VPS (Contabo)
- direnv for env vars

## 🌍 Links

- Website: https://moonshit.dev
- Subreddit: https://reddit.com/r/moonshitDEV
- Email: gitDEV@moonshit.download

## 🏷️ Badges

![License](https://img.shields.io/badge/license-MIT-green)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-blue)
![Issues](https://img.shields.io/github/issues/moonshitDEV/moonshitDEV)
![Stars](https://img.shields.io/github/stars/moonshitDEV/moonshitDEV?style=social)

## 🔄 Catch‑Up & Future

- Live site is up with minimal dashboard. Auth, Files API, and API keys are online; Reddit UI is next.
- Repository structure:
  - `projects/` — each app lives in its own folder (see `projects/dashboard/`)
  - `data_shit/` — ad‑hoc notes and logs not part of projects
- Technical docs for the dashboard project:
  - `projects/dashboard/README.md` (entry point)
  - `projects/dashboard/docs/README.md` (overview)
  - `projects/dashboard/docs/STATUS.md` (status and plan)
- Near‑term: improve login/error UX, wire read‑only Reddit views, tighten deploy flow, optional Redis for auth state.

## 🤝 Contribute

Fork it, hack it, and PR it. This repo is meant to grow with new endpoints, dashboards, and ideas.

## 📜 License

MIT License — feel free to use, remix, and contribute.
