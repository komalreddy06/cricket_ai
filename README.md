# 🏏 SRH Cricket AI — AI vs Human

> A real-time 3D cricket game where a human player competes against an intelligent AI agent powered by classical and modern AI algorithms.

---

## 📌 Academic Context

This project was built as part of the **Introduction to Artificial Intelligence** course (**EIE115R01**) to demonstrate all four units of the syllabus through a live, playable application — not just theory.

Every AI concept taught in the course has a direct role in the game:

| Syllabus Unit | Topic | How It's Used |
|---|---|---|
| Unit I | Search Algorithms | A* for fielder pathfinding · BFS for coverage · DFS for shot decisions |
| Unit II | CSP & Game Search | Minimax α-β for bowling/batting · CSP for field placement |
| Unit III | Bayesian Networks & MDP | Bayesian shot prediction · MDP strategy with Value Iteration |
| Unit IV | Reinforcement Learning | Q-Learning AI batting policy that improves over time |

---

## 🎮 What Is This?

A **browser-based 3D cricket game** where:
- **You** play as a human (bat or bowl)
- **The AI** plays as the SRH (Sunrisers Hyderabad) team
- The AI makes every decision using real algorithms — no hardcoded rules
- A live algorithm log shows the AI "thinking" in real time

**Stadium:** Rajiv Gandhi International Stadium, Hyderabad  
**Format:** 1, 3, or 5 overs per team  
**Theme:** SRH IPL team with real player names

---

## 🧠 AI Architecture

```
Human Action (browser)
        ↓
HTTP Request → Flask Python Server
        ↓
  ┌─────────────────────────────────────┐
  │  MDP → Minimax → Bayesian → CSP    │  (Bowling decision)
  │  Q-Learning → DFS → Minimax        │  (Batting decision)
  │  A* / BFS                          │  (Fielder movement)
  └─────────────────────────────────────┘
        ↓
JSON Response → Game Animates Result
```

---

## 📁 Project Structure

```
AI_Cricket_Game/
│
├── ai_server.py          ← Flask HTTP server — runs all AI
├── requirements.txt      ← Python dependencies
├── launch.bat            ← One-click launcher (Windows)
├── .gitignore
│
├── ai/                   ← AI algorithm modules
│   ├── search.py         ← A*, BFS, DFS
│   ├── csp.py            ← Constraint Satisfaction + Backtracking
│   ├── minimax.py        ← Minimax with Alpha-Beta Pruning
│   ├── bayesian.py       ← Bayesian Network + Belief Update
│   ├── mdp.py            ← Markov Decision Process + Value Iteration
│   └── rl.py             ← Q-Learning (learns across sessions)
│
├── frontend/
│   └── cricket.html      ← 3D game (Three.js) — runs in browser
│
├── data/
│   └── q_table_batting.json  ← AI learned batting memory
│
└── docs/
    └── cricket_guide.html    ← Step-by-step algorithm documentation
```

---

## 🚀 How to Run

**Requirements:** Python 3.8+, any modern browser

```bash
# Install dependencies
pip install flask flask-cors

# Start the AI server
python ai_server.py

# Open in browser
http://127.0.0.1:8888/
```

**Or just double-click `launch.bat`** — it does everything automatically.

---

## 🕹️ Controls

| Role | Key | Action |
|---|---|---|
| **Batting** | `1–6` | Select shot (Drive/Pull/Cut/Sweep/Flick/Loft) |
| | `← →` | Aim direction |
| | `SPACE` | Hit the ball (time it!) |
| | `W` | Toggle loft |
| **Bowling** | `Mouse move` | Aim on pitch |
| | `Click` | Deliver ball |
| | `F / S` | Fast or Spin |

---

## 🏆 SRH Playing XI

| # | Player | Role |
|---|---|---|
| 2 | Travis Head 🇦🇺 | Explosive Opener |
| 4 | Abhishek Sharma | Power Opener |
| 8 | Aiden Markram 🇿🇦 | Elegant No.3 |
| 11 | Heinrich Klaasen 🇿🇦 | Powerhouse WK |
| 9 | Nitish Kumar Reddy | All-rounder |
| 17 | Shahbaz Ahmed | Spin All-rounder |
| 7 | Pat Cummins 🇦🇺 ⭐ | Captain |
| 1 | Washington Sundar | Off-spin |
| 5 | Bhuvneshwar Kumar | Swing Bowler |
| 23 | T Natarajan | Yorker Specialist |
| 31 | Jaydev Unadkat | Left-arm Pacer |

---

## 🔬 Key Algorithm Details

### Q-Learning (Reinforcement Learning)
The AI batting agent learns from every ball it plays. The Q-table is saved to `data/q_table_batting.json` so the AI gets smarter across multiple sessions — no reset between games.

```
Q(state, action) ← Q(s,a) + α[r + γ·max Q(s',a') − Q(s,a)]
α = 0.12 | γ = 0.90 | ε: 0.35 → 0.05
```

### Minimax with Alpha-Beta Pruning
The AI bowler evaluates all possible deliveries against the human's likely responses, pruning branches that can't improve the result — reducing game-state evaluation by ~65%.

### CSP Field Placement
9 fielders are placed using constraint backtracking with MRV and LCV heuristics, ensuring no zone overlap while maximising coverage of the Bayesian Network's predicted shot directions.

### MDP Strategy
Value Iteration is run at server startup, pre-computing the optimal bowling strategy for every possible game state (balls remaining × runs to defend × wickets taken).

---

## 📊 Tech Stack

- **Frontend:** HTML, JavaScript, Three.js (3D rendering)
- **Backend:** Python, Flask, Flask-CORS
- **AI:** Pure Python (no external AI libraries — all algorithms from scratch)

---

*Built with Python + Three.js | All AI algorithms implemented from scratch*
