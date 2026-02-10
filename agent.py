import json
import random
import sys
import time

directions = ["left", "right"]

def evaluate_state(fighter_info, opponent_info) -> float:
    fx, fy = fighter_info["x"], fighter_info["y"]
    ox, oy = opponent_info["x"], opponent_info["y"]

    adx = abs(ox - fx)
    ady = abs(oy - fy)

    fh = fighter_info["health"]
    oh = opponent_info["health"]

    light_cd, heavy_cd = fighter_info["attack_cooldown"]
    dash_cd = fighter_info["dash_cooldown"]

    opp_attacking = opponent_info["attacking"]
    opp_jumping = opponent_info.get("jump", False)
    me_jumping = fighter_info["jump"]

    in_attack_range = (adx <= 160) and (ady <= 120)

    score = 0.0

    # health difference
    score += 3.0 * (fh - oh)

    # encourage being close
    if in_attack_range:
        score += 80.0
    else:
        score -= 0.2 * adx

    # STRONG encourage attack availability
    if in_attack_range and light_cd <= 0:
        score += 100.0
    if in_attack_range and heavy_cd <= 0:
        score += 140.0

    # NEW: jump logic
    if opp_jumping and in_attack_range:
        if me_jumping:
            score += 60.0      # defensive jump success
        else:
            score -= 80.0      # stayed grounded → bad

    # discourage pure retreat
    if adx > 260:
        score -= 70.0

    # dash is situational
    if dash_cd == 0 and opp_attacking:
        score += 15.0

    return score



def simulate_next_state(fighter_info, opponent_info, action):
    f = dict(fighter_info)
    o = dict(opponent_info)

    SPEED = 5
    DASH_SPEED = 30
    LIGHT_DMG = 10
    HEAVY_DMG = 20

    # defaults
    f.setdefault("attack_cooldown", [0, 0])
    f.setdefault("dash_cooldown", 999999)
    f.setdefault("attacking", False)
    f.setdefault("jump", False)

    # move
    if action["move"] == "left":
        f["x"] -= SPEED
    elif action["move"] == "right":
        f["x"] += SPEED

    # dash
    if action["dash"] in ("left", "right") and f["dash_cooldown"] == 0:
        f["x"] += (-DASH_SPEED if action["dash"] == "left" else DASH_SPEED)
        f["dash_cooldown"] = 50

    # tick cooldowns
    f["attack_cooldown"][0] = max(0, f["attack_cooldown"][0] - 1)
    f["attack_cooldown"][1] = max(0, f["attack_cooldown"][1] - 1)
    f["dash_cooldown"] = max(0, f["dash_cooldown"] - 1)
    f["attacking"] = False  # reset each frame

    # attack range
    in_attack_range = (abs(o["x"] - f["x"]) <= 160) and (abs(o["y"] - f["y"]) <= 120)

    # attack logic
    if action["attack"] == 1 and f["attack_cooldown"][0] == 0:
        f["attacking"] = True
        f["attack_cooldown"][0] = 25
        if in_attack_range:
            o["health"] = max(0, o["health"] - LIGHT_DMG)
        else:
            f["health"] -= 3  # punish whiff

    elif action["attack"] == 2 and f["attack_cooldown"][1] == 0:
        f["attacking"] = True
        f["attack_cooldown"][1] = 100
        if in_attack_range:
            o["health"] = max(0, o["health"] - HEAVY_DMG)
        else:
            f["health"] -= 6  # heavier punish

    return f, o


def choose_action_by_heuristic(fighter_info, opponent_info) -> dict:
    fx = fighter_info["x"]
    ox = opponent_info["x"]
    enemy_right = ox > fx

    # Candidate actions (small, safe set)
    candidates = [
        {"move": None, "attack": None, "jump": False, "dash": None},
        {"move": "right" if enemy_right else "left", "attack": None, "jump": False, "dash": None},  # approach
        {"move": "left" if enemy_right else "right", "attack": None, "jump": False, "dash": None},  # retreat
        {"move": None, "attack": 1, "jump": False, "dash": None},  # light
        {"move": None, "attack": 2, "jump": False, "dash": None},  # heavy
    ]

    # Add dash options if available
    if fighter_info["dash_cooldown"] == 0:
        candidates.append({"move": None, "attack": None, "jump": False, "dash": "right" if enemy_right else "left"})
        candidates.append({"move": None, "attack": None, "jump": False, "dash": "left" if enemy_right else "right"})

    best = candidates[0]
    best_score = -1e18

    for a in candidates:
        nf, no = simulate_next_state(fighter_info, opponent_info, a)
        s = evaluate_state(nf, no)
        if s > best_score:
            best_score = s
            best = a

    best = dict(best)
    best["debug"] = None  
    return best

def generate_actions(f_info, o_info):
    fx, fy = f_info["x"], f_info["y"]
    ox, oy = o_info["x"], o_info["y"]
    enemy_right = ox > fx

    actions = [
        # idle
        {"move": None, "attack": None, "jump": False, "dash": None, "debug": None},

        # approach / retreat
        {"move": "right" if enemy_right else "left", "attack": None, "jump": False, "dash": None, "debug": None},
        {"move": "left" if enemy_right else "right", "attack": None, "jump": False, "dash": None, "debug": None},

        # attacks
        {"move": None, "attack": 1, "jump": False, "dash": None, "debug": None},
        {"move": None, "attack": 2, "jump": False, "dash": None, "debug": None},

        # jump (NEW)
        {"move": None, "attack": None, "jump": True, "dash": None, "debug": None},
    ]

    dash_cd = f_info.get("dash_cooldown", 999999)
    if dash_cd == 0:
        actions.append({
            "move": None,
            "attack": None,
            "jump": False,
            "dash": "right" if enemy_right else "left",
            "debug": None
        })

    return actions


def minimax_alpha_beta(f_info, o_info, depth, alpha, beta, maximizing_player):
    """
    maximizing_player=True  -> our turn
    maximizing_player=False -> opponent turn (minimize our score)
    """
    if depth == 0 or f_info["health"] <= 0 or o_info["health"] <= 0:
        return evaluate_state(f_info, o_info), None

    if maximizing_player:
        best_score = -1e18
        best_action = None
        for a in generate_actions(f_info, o_info):
            nf, no = simulate_next_state(f_info, o_info, a)
            score, _ = minimax_alpha_beta(nf, no, depth - 1, alpha, beta, False)
            if score > best_score:
                best_score = score
                best_action = a
            alpha = max(alpha, best_score)
            if beta <= alpha:
                break
        return best_score, best_action
    else:
        # Opponent acts: minimize our evaluation
        worst_score = 1e18
        for a in generate_actions(o_info, f_info):
            # simulate opponent action by swapping roles, then swap back
            no2, nf2 = simulate_next_state(o_info, f_info, a)
            score, _ = minimax_alpha_beta(nf2, no2, depth - 1, alpha, beta, True)
            if score < worst_score:
                worst_score = score
            beta = min(beta, worst_score)
            if beta <= alpha:
                break
        return worst_score, None
    
def choose_action_minimax(fighter_info, opponent_info, depth=2):
    # depth=2 usually safe under 0.4s with small branching
    _, best = minimax_alpha_beta(
        fighter_info, opponent_info,
        depth=depth,
        alpha=-1e18, beta=1e18,
        maximizing_player=True
    )
    if best is None:
        # fallback (do nothing)
        best = {"move": None, "attack": None, "jump": False, "dash": None, "debug": None}
    return best

def make_move(fighter_info, opponent_info, saved_data) -> dict:
    action = {
        "move": None,
        "attack": None,
        "jump": False,
        "dash": None,
        "debug": None,
        "saved_data": saved_data,
    }

    # ===== PHASE 4: GUARANTEED ATTACK =====
    dx = abs(fighter_info["x"] - opponent_info["x"])
    dy = abs(fighter_info["y"] - opponent_info["y"])

    in_attack_range = (dx <= 160) and (dy <= 120)
    light_cd, heavy_cd = fighter_info["attack_cooldown"]
    is_attacking = fighter_info["attacking"]

    if in_attack_range and not is_attacking:
        if heavy_cd == 0:
            action["attack"] = 2
            return action
        elif light_cd == 0:
            action["attack"] = 1
            return action

    # ===== PHASE 3: ANTI-AIR / DEFENSIVE JUMP =====
    if opponent_info["y"] < fighter_info["y"] - 40:
        action["jump"] = True

    # ===== PHASE 2: BASIC POSITIONING =====
    enemy_right = opponent_info["x"] > fighter_info["x"]

    if not in_attack_range:
        action["move"] = "right" if enemy_right else "left"
    else:
        # small retreat when too close and can't attack
        if light_cd > 0 and heavy_cd > 0:
            action["move"] = "left" if enemy_right else "right"

    # ===== SAFE FALLBACK =====
    if not isinstance(saved_data, dict):
        saved_data = {}
    saved_data["frame"] = saved_data.get("frame", 0) + 1
    action["saved_data"] = saved_data

    return action


try:
    input_data = input()
    json_data = json.loads(input_data)
    opponent_info = json_data["opponent"]
    fighter_info = json_data["fighter"]
    saved_data = json_data["saved_data"]
    result = make_move(fighter_info, opponent_info, saved_data)
    print(json.dumps(result))
except Exception:
    print(json.dumps({
        "move": None, "attack": None, "jump": False, "dash": None,
        "debug": None, "saved_data": {}
    }))