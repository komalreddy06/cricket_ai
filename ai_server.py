"""
Cricket AI Server  —  EIE115R01  (Flask HTTP Edition)
======================================================
HTTP server on port 8888 — open http://127.0.0.1:8888/ to play!

Endpoints:
  GET  /              → serves cricket.html game
  GET  /status        → health check
  POST /bowl_decision → Unit II+III: Minimax + MDP picks delivery
  POST /shot_decision → Unit I+II+IV: DFS + Minimax + Q-Learning picks shot
  POST /field_placement → Unit II+III: CSP + Bayesian places fielders
  POST /fielder_path  → Unit I: A* path for fielder
  POST /learn_update  → Unit IV: Q-table + Bayesian belief update
"""

import os
import logging
import threading

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from ai.search   import AStarFielder, DFSShotTree
from ai.csp      import FieldPlacementCSP
from ai.minimax  import CricketMinimax
from ai.bayesian import CricketBayesianNetwork
from ai.mdp      import CricketMDP
from ai.rl       import CricketQLearning

# ── Logging ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("CricketAI")

# ── Flask App ────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)  # Allow browser fetch() from file:// or localhost

# ── Initialise AI Modules ────────────────────────────────────────────
log.info("=" * 60)
log.info("   🏏  SRH Cricket AI Server — EIE115R01 (Flask HTTP)")
log.info("=" * 60)
log.info("Initialising AI modules …")

astar    = AStarFielder()           # Unit I  — A* Search
dfs      = DFSShotTree()            # Unit I  — DFS Shot Tree
csp      = FieldPlacementCSP()      # Unit II — CSP / Field Placement
minimax  = CricketMinimax()         # Unit II — Minimax + Alpha-Beta
bayesian = CricketBayesianNetwork() # Unit III— Bayesian Network
mdp      = CricketMDP()             # Unit III— Markov Decision Process
rl       = CricketQLearning()       # Unit IV — Q-Learning

log.info("Running MDP Value Iteration …")
mdp.value_iteration()

shot_history: list[str] = []
_lock = threading.Lock()
log.info("All AI modules ready ✓")
log.info("-" * 60)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ─────────────────────────────────────────────────────────────────────
# 0. Serve Game — open http://127.0.0.1:8888/ to play!
# ─────────────────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def index():
    """Serve cricket.html so the user just opens http://127.0.0.1:8888/"""
    return send_from_directory(BASE_DIR, "cricket.html")


# ─────────────────────────────────────────────────────────────────────
# 1. Health Check
# ─────────────────────────────────────────────────────────────────────
@app.route("/status", methods=["GET"])
def status():
    return jsonify({
        "status":  "ok",
        "message": "SRH Cricket AI Online ✓",
        "units":   ["I: BFS/DFS/A*", "II: Minimax/CSP", "III: Bayesian/MDP", "IV: Q-Learning"],
    })


# ─────────────────────────────────────────────────────────────────────
# 2. Bowl Decision  (Units I + II + III)
# ─────────────────────────────────────────────────────────────────────
@app.route("/bowl_decision", methods=["POST"])
def bowl_decision():
    req = request.get_json(force=True) or {}
    balls_rem  = req.get("balls_remaining", 6)
    wickets    = req.get("wickets_taken",   0)
    runs_def   = req.get("runs_to_defend",  30)
    last_shots = req.get("last_shots",      [])

    # Unit III — MDP: high-level strategy
    strategy = mdp.get_optimal_action(balls_rem, runs_def, wickets)
    log.info("[MDP]     strategy → %s  (balls=%d, runs_def=%d, wkts=%d)",
             strategy, balls_rem, runs_def, wickets)

    # Unit II — Minimax α-β: pick optimal delivery
    ctx = {
        "balls_left":     balls_rem,
        "wickets_taken":  wickets,
        "runs_to_defend": runs_def,
        "human_position": req.get("batsman_position", "off_stump"),
        "pitch_spin":     req.get("pitch_spin", False),
    }
    delivery = minimax.get_best_bowl(ctx, mdp_strategy=strategy)
    log.info("[Minimax] delivery → %s @ (%.2f,%.2f) spd=%.0f",
             delivery["bowl_type"], delivery["target_x"],
             delivery["target_z"],  delivery["speed"])

    # Unit III — Bayesian: predict shot, adjust field
    shot_dist = bayesian.predict_shot(
        delivery["target_x"], delivery["target_z"],
        last_shots or shot_history
    )
    log.info("[Bayesian] top shots → %s",
             sorted(shot_dist.items(), key=lambda x: -x[1])[:3])

    # Unit II — CSP: optimal field placement
    positions, assignment = csp.solve(shot_dist)
    log.info("[CSP]     placed %d fielders", len(positions))

    return jsonify({
        **delivery,
        "field_positions": positions,
        "shot_prediction": shot_dist,
        "mdp_strategy":    strategy,
        "algo":            "Minimax α-β + MDP + Bayesian + CSP",
    })


# ─────────────────────────────────────────────────────────────────────
# 3. Shot Decision  (Units I + II + IV)
# ─────────────────────────────────────────────────────────────────────
@app.route("/shot_decision", methods=["POST"])
def shot_decision():
    req = request.get_json(force=True) or {}
    bowl_type = req.get("bowl_type",       "fast")
    tx        = req.get("target_x",         0.0)
    tz        = req.get("target_z",          7.5)
    speed     = req.get("speed",           130.0)
    field_pos = req.get("field_positions",   [])

    # Unit IV — Q-Learning
    btype, line, length = rl.classify_delivery(tx, tz, bowl_type)
    rl_action = rl.get_action(btype, line, length)
    log.info("[QL]      action → %s  state=(%s|%s|%s)", rl_action, btype, line, length)

    # Unit I — DFS shot decision tree
    dfs_shot = dfs.dfs_select_shot(tx, tz, 0.6)
    log.info("[DFS]     shot → %s", dfs_shot)

    # Unit II — Minimax final shot
    delivery_info = {"bowl_type": bowl_type, "target_x": tx, "target_z": tz, "speed": speed}
    mm_shot = minimax.get_best_shot(delivery_info, field_pos, rl_suggestion=rl_action)
    log.info("[Minimax] shot → %s  dir=%.1f°", mm_shot["shot_type"], mm_shot["direction"])

    # Unit III — Bayesian timing
    timing = bayesian.estimate_timing(bowl_type, speed)

    return jsonify({
        **mm_shot,
        "timing":         timing,
        "rl_suggestion":  rl_action,
        "dfs_suggestion": dfs_shot,
        "algo":           "Q-Learning + Minimax α-β + DFS + Bayesian",
    })


# ─────────────────────────────────────────────────────────────────────
# 4. Field Placement  (Units II + III)
# ─────────────────────────────────────────────────────────────────────
@app.route("/field_placement", methods=["POST"])
def field_placement():
    req = request.get_json(force=True) or {}
    tx         = req.get("target_x",  0.0)
    tz         = req.get("target_z",  7.5)
    last_shots = req.get("last_shots", [])

    shot_dist = bayesian.predict_shot(tx, tz, last_shots)
    positions, assignment = csp.solve(shot_dist)

    return jsonify({
        "field_positions":  positions,
        "zone_assignment":  assignment,
        "shot_distribution": shot_dist,
        "algo":             "CSP + Bayesian Network",
    })


# ─────────────────────────────────────────────────────────────────────
# 5. Fielder Path — A* (Unit I)
# ─────────────────────────────────────────────────────────────────────
@app.route("/fielder_path", methods=["POST"])
def fielder_path():
    req   = request.get_json(force=True) or {}
    start = tuple(req.get("start", [0.0,  0.0]))
    goal  = tuple(req.get("goal",  [10.0, 10.0]))
    path  = astar.find_path(start, goal)
    return jsonify({"path": path, "algo": "A* Search (Unit I)"})


# ─────────────────────────────────────────────────────────────────────
# 6. Learn Update  (Units III + IV)
# ─────────────────────────────────────────────────────────────────────
@app.route("/learn_update", methods=["POST"])
def learn_update():
    global shot_history
    req       = request.get_json(force=True) or {}
    bowl_type = req.get("bowl_type",    "fast")
    tx        = req.get("target_x",      0.0)
    tz        = req.get("target_z",       7.5)
    action    = req.get("shot_taken",   "defend")
    runs      = req.get("runs_scored",    0)
    got_out   = req.get("got_out",       False)

    # Unit IV — Q-Learning Bellman update
    btype, line, length = rl.classify_delivery(tx, tz, bowl_type)
    reward = rl.compute_reward(runs, got_out)
    rl.update(btype, line, length, action, reward, btype, line, length)
    log.info("[QL]      update: r=%.1f  ε=%.3f  ep=%d", reward, rl.epsilon, rl.episode)

    # Unit III — Bayesian belief update
    direction = req.get("shot_direction", None)
    bayesian.update(tx, tz, action, direction)

    if action:
        with _lock:
            shot_history = (shot_history + [action])[-10:]

    return jsonify({"status": "updated", "reward": reward, "epsilon": rl.epsilon})


# ─────────────────────────────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    log.info("🏏  Starting Flask server → http://127.0.0.1:8888")
    log.info("   Unit I: A*/BFS/DFS  |  Unit II: Minimax/CSP")
    log.info("   Unit III: Bayesian/MDP  |  Unit IV: Q-Learning")
    log.info("=" * 60)
    app.run(host="127.0.0.1", port=8888, debug=False, threaded=True)
