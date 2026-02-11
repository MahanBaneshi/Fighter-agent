import json
import random
import sys
import time

directions = ["left", "right"]

def evaluate_state(fighter_info, opponent_info) -> float:
    fx, fy = fighter_info["x"], fighter_info["y"]
    ox, oy = opponent_info["x"], opponent_info["y"]

    dx = ox - fx
    dy = oy - fy
    adx = abs(dx)
    ady = abs(dy)

    fh = fighter_info["health"]
    oh = opponent_info["health"]

    light_cd, heavy_cd = fighter_info["attack_cooldown"]
    dash_cd = fighter_info["dash_cooldown"]

    opp_attacking = opponent_info["attacking"]
    me_attacking = fighter_info["attacking"]

    # Approximation of being in attack range
    # (actual game uses rectangle collision)
    in_attack_range = (adx <= 160) and (ady <= 120)

    score = 0.0

    # 1) Main objective: health difference
    score += 5.0 * (fh - oh)

    # 2) Distance to opponent (prefer being in attack range)
    if in_attack_range:
        score += 80.0
    else:
        # Penalize large horizontal distance
        score -= 0.15 * adx

    # 3) Attack availability (cooldowns)
    if light_cd <= 0:
        score += 12.0
    else:
        score -= 0.2 * light_cd

    if heavy_cd <= 0:
        score += 18.0
    else:
        score -= 0.15 * heavy_cd

    # 4) Danger: opponent attacking while close
    if opp_attacking and in_attack_range:
        score -= 40.0

    # 5) Dash availability (for engage or escape)
    if dash_cd <= 0:
        score += 6.0
    else:
        score -= 0.05 * dash_cd

    # 6) Jump has no score effect for now

    return score


def simulate_next_state(fighter_info, opponent_info, action):
    f = dict(fighter_info)
    o = dict(opponent_info)

    SPEED = 5
    DASH_SPEED = 30
    LIGHT_DMG = 10
    HEAVY_DMG = 20

    WIDTH = 120
    HEIGHT = 180

    f.setdefault("attack_cooldown", [0, 0])
    f.setdefault("dash_cooldown", 999999)
    f.setdefault("attacking", False)
    f.setdefault("jump", False)

    # movement
    if action["move"] == "left":
        f["x"] -= SPEED
    elif action["move"] == "right":
        f["x"] += SPEED

    # dash
    if action["dash"] in ("left", "right") and f["dash_cooldown"] == 0:
        f["x"] += (-DASH_SPEED if action["dash"] == "left" else DASH_SPEED)
        f["dash_cooldown"] = 50

    # cooldown tick
    f["attack_cooldown"][0] = max(0, f["attack_cooldown"][0] - 1)
    f["attack_cooldown"][1] = max(0, f["attack_cooldown"][1] - 1)
    f["dash_cooldown"] = max(0, f["dash_cooldown"] - 1)
    f["attacking"] = False

    # facing direction
    enemy_right = o["x"] > f["x"]
    flip = not enemy_right

    # attack rect
    attack_x = f["x"] - (WIDTH if flip else 0)
    attack_y = f["y"] - HEIGHT // 2

    attack_rect = {
        "left": attack_x,
        "right": attack_x + WIDTH,
        "top": attack_y,
        "bottom": attack_y + HEIGHT
    }

    opponent_rect = {
        "left": o["x"] - WIDTH // 2,
        "right": o["x"] + WIDTH // 2,
        "top": o["y"] - HEIGHT // 2,
        "bottom": o["y"] + HEIGHT // 2
    }

    def collide(r1, r2):
        return not (
            r1["right"] < r2["left"] or
            r1["left"] > r2["right"] or
            r1["bottom"] < r2["top"] or
            r1["top"] > r2["bottom"]
        )

    # attack
    if action["attack"] == 1 and f["attack_cooldown"][0] == 0:
        f["attacking"] = True
        f["attack_cooldown"][0] = 25
        if collide(attack_rect, opponent_rect):
            o["health"] = max(0, o["health"] - LIGHT_DMG)
        else:
            f["health"] -= 2

    elif action["attack"] == 2 and f["attack_cooldown"][1] == 0:
        f["attacking"] = True
        f["attack_cooldown"][1] = 100
        if collide(attack_rect, opponent_rect):
            o["health"] = max(0, o["health"] - HEAVY_DMG)
        else:
            f["health"] -= 4

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
    best["debug"] = None  # یا best_score برای دیباگ
    return best



def generate_actions(f_info, o_info):
    fx = f_info["x"]
    ox = o_info["x"]
    enemy_right = ox > fx

    actions = [
        {"move": None, "attack": None, "jump": False, "dash": None, "debug": None},
        {"move": "right" if enemy_right else "left", "attack": None, "jump": False, "dash": None, "debug": None},
        {"move": "left" if enemy_right else "right", "attack": None, "jump": False, "dash": None, "debug": None},
        {"move": None, "attack": 1, "jump": False, "dash": None, "debug": None},
        {"move": None, "attack": 2, "jump": False, "dash": None, "debug": None},
    ]

    dash_cd = f_info.get("dash_cooldown", 999999)  # <-- مهم
    if dash_cd == 0:
        actions.append({"move": None, "attack": None, "jump": False, "dash": "right" if enemy_right else "left", "debug": None})
        actions.append({"move": None, "attack": None, "jump": False, "dash": "left" if enemy_right else "right", "debug": None})

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

    # pick action using miniMax chooser
    picked = choose_action_minimax(fighter_info, opponent_info, depth=2)

    action["move"] = picked["move"]
    action["attack"] = picked["attack"]
    action["jump"] = picked["jump"]
    action["dash"] = picked["dash"]
    action["debug"] = picked.get("debug", None)

    # keep saved_data small and stable
    if not isinstance(saved_data, dict):
        saved_data = {}
    saved_data["frame"] = int(saved_data.get("frame", 0)) + 1
    action["saved_data"] = saved_data

    # edge guard
    MARGIN = 90
    if fighter_info["x"] < MARGIN:
        if action["move"] == "left": action["move"] = None
        if action["dash"] == "left": action["dash"] = None
    if fighter_info["x"] > 1000 - MARGIN:
        if action["move"] == "right": action["move"] = None
        if action["dash"] == "right": action["dash"] = None


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