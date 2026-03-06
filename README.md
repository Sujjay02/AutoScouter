# 🤖 FRC AutoScouter — FRC 2026

AI-powered FRC match scouter that analyzes Twitch livestreams in real time using **Claude Vision**, ranking robots across 8 performance categories.

## Features

- **Live Twitch stream capture** via `streamlink` + OpenCV
- **Claude Vision AI** analyzes frames every 5 seconds — detects robot numbers, actions, game pieces, climbs, penalties
- **8 scoring categories**: Auto, Teleop, Coral Handling, Algae Handling, Defense, Endgame, Consistency, Speed
- **Weighted overall ranking** across all scouted teams
- **The Blue Alliance integration** — auto-fills alliance compositions from match keys
- **Real-time WebSocket dashboard** — live feed panel updates as frames are analyzed
- **Team profiles** with radar charts, full history, and manual scout notes
- **Mock stream mode** for testing without a live Twitch feed

## Quick Start

### 1. Install dependencies

```bash
# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### 3. Run in development

```bash
./scripts/run_dev.sh
```

- Frontend: http://localhost:3000
- API + docs: http://localhost:8000/docs

### 4. Production build

```bash
./scripts/build_and_serve.sh
# Everything served from http://localhost:8000
```

## Usage

1. Open the dashboard → **Scout** tab
2. Enter your **Match Key** (e.g. `2025casd_qm1`) and **Twitch channel** (e.g. `firstinspires`)
3. Optionally enter alliance team numbers or a TBA match key to auto-fill them
4. Click **Start Scouting** — the AI begins analyzing frames every 5 seconds
5. Watch the **Live Feed** panel and **Rankings** update in real time
6. Click any team number to see their full performance profile

## FRC 2026 Game Overview

- **FUEL**: Bright yellow foam balls (~5.91") scored into the **Hub** for 1 pt each. No holding limit; robots preload up to 8.
- **Auto (20 sec)**: Score FUEL into Hub. Up to 2 robots per alliance can earn a bonus by completing an **L1 Tower climb** before Auto ends.
- **Teleop (~2 min 10 sec)**: Driver-controlled FUEL cycles — collect from **Depot** or **Outpost** human player → shoot into **Hub**.
- **Endgame (final 30 sec)**: Climb the **Tower** (no parking points). Three levels: L1 (lowest rung), L2 (bumpers above rung 1), L3 (highest).
- **Trench**: Low tunnel (~22") robots can use to bypass the **Bump** for faster cycling.

## Scouting Categories

| Category | Description | Weight |
|---|---|---|
| Auto Period | FUEL scored in Hub + L1 climb bonus during 20-sec auto | 1.5× |
| FUEL Scoring | Yellow foam balls scored into the Hub during teleop | 1.2× |
| Tower Climb | Endgame climb level achieved (L1 / L2 / L3) | 1.4× |
| Collection | Efficiency collecting FUEL from Depot or Outpost | 1.0× |
| Defense | Defensive plays and opponent disruption | 0.8× |
| Trench Usage | Using the Trench tunnel to bypass the Bump | 0.7× |
| Consistency | Reliability and avoiding penalties | 1.0× |
| Speed & Cycling | FUEL cycle time (Depot → Hub round trip) | 0.9× |

## API Reference

Full interactive docs at `/docs` when the server is running.

| Endpoint | Description |
|---|---|
| `POST /api/matches/start` | Start scouting a match |
| `POST /api/matches/{key}/stop` | Stop scouting |
| `GET /api/rankings?category=auto_scoring` | Get ranked team list |
| `GET /api/teams/{number}` | Full team profile |
| `PATCH /api/teams/{number}/notes` | Add scout notes |
| `GET /api/matches` | List all scouted matches |
| `WS /ws` | Real-time frame result stream |

## Architecture

```
Twitch Stream
     │
     ▼
StreamCapture (streamlink + OpenCV)
     │  frame every 5s (base64 JPEG)
     ▼
Claude Vision API (claude-opus-4-6)
     │  structured JSON
     ▼
ScouterEngine  ──► SQLite (robot observations, team stats)
     │
     ▼
FastAPI  ──► WebSocket broadcast ──► React Dashboard
```

## Requirements

- Python 3.11+
- Node.js 20+
- `streamlink` (installed via pip, or system package)
- Anthropic API key
- (Optional) The Blue Alliance API key
