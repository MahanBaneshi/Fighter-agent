import json
import random
import sys
import time

directions = ["left", "right"]

def evaluate_state(fighter_info, opponent_info) -> float:
    fx, fy = fighter_info["x"], fighter_info["y"]
    ox, oy = opponent_info["x"], opponent_info["y"]

    fh = fighter_info["health"]
    oh = opponent_info["health"]

    light_cd, heavy_cd = fighter_info["attack_cooldown"]
    dash_cd = fighter_info.get("dash_cooldown", 999999)

    HIT_W, HIT_H = 120, 180

    # rects
    f_top = fy - HIT_H // 2
    o_left = ox - HIT_W // 2
    o_top = oy - HIT_H // 2
    o_rect = (o_left, o_top, HIT_W, HIT_H)

    flip = (ox < fx)
    atk_left = fx - (HIT_W if flip else 0)
    atk_top = f_top
    atk_rect = (atk_left, atk_top, HIT_W, HIT_H)

    def collide(a, b):
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        return (ax < bx + bw) and (ax + aw > bx) and (ay < by + bh) and (ay + ah > by)

    in_attack_range = collide(atk_rect, o_rect)

    dx = abs(ox - fx)
    dy = abs(oy - fy)

    score = 0.0

    # health
    score += 3.0 * (fh - oh)

    # spacing
    if in_attack_range:
        score += 80.0
    else:
        score -= 0.2 * dx

    # attack ready
    if in_attack_range and light_cd <= 0:
        score += 100.0
    if in_attack_range and heavy_cd <= 0:
        score += 140.0

    # anti-air
    opp_jumping = opponent_info.get("jump", False)
    me_jumping = fighter_info.get("jump", False)
    if opp_jumping and in_attack_range:
        score += 60.0 if me_jumping else -80.0

    # far penalty
    if dx > 260:
        score -= 70.0

    # dash situational
    if dash_cd == 0 and opponent_info.get("attacking", False):
        score += 15.0

    return score


def simulate_next_state(fighter_info, opponent_info, action):
    f = dict(fighter_info)
    o = dict(opponent_info)

    SPEED = 5
    DASH_SPEED_PER_FRAME = 30
    DASH_FRAMES = 10
    DASH_TOTAL = DASH_SPEED_PER_FRAME * DASH_FRAMES  # 300
    LIGHT_DMG = 10
    HEAVY_DMG = 20
    HIT_W, HIT_H = 120, 180

    f.setdefault("attack_cooldown", [0, 0])
    f.setdefault("dash_cooldown", 0)
    f.setdefault("attacking", False)
    f.setdefault("jump", False)

    # move
    if action.get("move") == "left":
        f["x"] -= SPEED
    elif action.get("move") == "right":
        f["x"] += SPEED

    # dash (full 10 frames)
    if action.get("dash") in ("left", "right") and f.get("dash_cooldown", 0) == 0:
        f["x"] += (-DASH_TOTAL if action["dash"] == "left" else DASH_TOTAL)
        f["dash_cooldown"] = 50

    # cooldowns
    f["attack_cooldown"][0] = max(0, f["attack_cooldown"][0] - 1)
    f["attack_cooldown"][1] = max(0, f["attack_cooldown"][1] - 1)
    f["dash_cooldown"] = max(0, f.get("dash_cooldown", 0) - 1)

    f["attacking"] = False

    # rects
    f_top = f["y"] - HIT_H // 2
    o_rect = (o["x"] - HIT_W // 2, o["y"] - HIT_H // 2, HIT_W, HIT_H)

    flip = (o["x"] < f["x"])
    atk_rect = (f["x"] - (HIT_W if flip else 0), f_top, HIT_W, HIT_H)

    def collide(a, b):
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        return (ax < bx + bw) and (ax + aw > bx) and (ay < by + bh) and (ay + ah > by)

    # attack
    atk = action.get("attack")
    if atk == 1 and f["attack_cooldown"][0] == 0:
        f["attacking"] = True
        f["attack_cooldown"][0] = 25
        if collide(atk_rect, o_rect):
            o["health"] = max(0, o["health"] - LIGHT_DMG)

    elif atk == 2 and f["attack_cooldown"][1] == 0:
        f["attacking"] = True
        f["attack_cooldown"][1] = 100
        if collide(atk_rect, o_rect):
            o["health"] = max(0, o["health"] - HEAVY_DMG)

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
    if not isinstance(saved_data, dict):
        saved_data = {}

    fx, fy = fighter_info["x"], fighter_info["y"]
    ox, oy = opponent_info["x"], opponent_info["y"]

    light_cd, heavy_cd = fighter_info["attack_cooldown"]
    opp_attacking = opponent_info.get("attacking", False)

    HIT_W, HIT_H = 120, 180

    def collide(a, b):
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        return (ax < bx + bw) and (ax + aw > bx) and (ay < by + bh) and (ay + ah > by)

    def in_range(fx_, fy_, ox_, oy_):
        f_top = fy_ - HIT_H // 2
        o_rect = (ox_ - HIT_W // 2, oy_ - HIT_H // 2, HIT_W, HIT_H)
        flip = (ox_ < fx_)
        atk_rect = (fx_ - (HIT_W if flip else 0), f_top, HIT_W, HIT_H)
        return collide(atk_rect, o_rect)

    enemy_right = ox > fx
    dx = abs(ox - fx)
    in_attack_range = in_range(fx, fy, ox, oy)

    # emergency defense
    if opp_attacking and dx < 220:
        action = {
            "move": "left" if enemy_right else "right",
            "attack": None,
            "jump": (dx < 160),
            "dash": None,
            "debug": None,
            "saved_data": saved_data,
        }
        saved_data["frame"] = saved_data.get("frame", 0) + 1
        action["saved_data"] = saved_data
        return action

    # quick anti-air
    if opponent_info["y"] < fighter_info["y"] - 40 and dx < 220:
        action = {
            "move": "left" if enemy_right else "right" if dx < 180 else None,
            "attack": None,
            "jump": True,
            "dash": None,
            "debug": None,
            "saved_data": saved_data,
        }
        saved_data["frame"] = saved_data.get("frame", 0) + 1
        action["saved_data"] = saved_data
        return action

    # opportunistic hit
    if in_attack_range and (not fighter_info.get("attacking", False)):
        if light_cd == 0:
            action = {"move": None, "attack": 1, "jump": False, "dash": None, "debug": None, "saved_data": saved_data}
            saved_data["frame"] = saved_data.get("frame", 0) + 1
            action["saved_data"] = saved_data
            return action
        if heavy_cd == 0 and (not opp_attacking):
            action = {"move": None, "attack": 2, "jump": False, "dash": None, "debug": None, "saved_data": saved_data}
            saved_data["frame"] = saved_data.get("frame", 0) + 1
            action["saved_data"] = saved_data
            return action

    # minimax decision
    best = choose_action_minimax(fighter_info, opponent_info, depth=2)
    action = {
        "move": best.get("move"),
        "attack": best.get("attack"),
        "jump": bool(best.get("jump", False)),
        "dash": best.get("dash"),
        "debug": best.get("debug", None),
        "saved_data": saved_data,
    }

    saved_data["frame"] = saved_data.get("frame", 0) + 1
    action["saved_data"] = saved_data

    action["debug"] = {
        # "enemy_direction": directions[enemy_direction],
        # "should_we_attack": should_we_attack,
        # "move_towards": move_towards,
        # "should_run": should_run,
        # "attacks_available": attacks_available,
        # "if_attacks_available": if_attacks_available,
        "figher_info": fighter_info,
        # "dash": action["dash"],
        # "move": action["move"],
    }
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