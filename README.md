game files: https://drive.google.com/file/d/1MrrGC5PBFbjgwXO0IRgbYSHRQ-CFGYbd/view?usp=sharing

# Fighter AI Project

## Project Overview

This project implements an AI agent for a 2D fighting game environment.  
The goal of the project was to design an intelligent decision-making agent capable of defeating a random opponent using heuristic evaluation and adversarial search techniques.

The strongest and final version of the AI agent is implemented in:

```
agent3.py
```

Other files such as `GAMECODE-python.py` and `fighter.py` belong to the game engine and are not part of the AI logic.

---

## How to Run the Game

The game asset files (graphics, sounds, etc.) are provided as a ZIP file in the repository.

### Steps to run:

1. Download the repository.
2. Extract the ZIP file containing the game assets.
3. Place the extracted folders next to the Python source files.
4. Run the following file:

```
GAMECODE-python.py
```

The AI vs AI mode will automatically execute using `agent3.py` as the main intelligent agent.

---

# Game Rules Summary

- Each fighter starts with 100 HP.
- The game ends when one fighter’s HP reaches 0.
- Movement speed: 5 units per frame.
- Dash:
  - Moves the fighter 300 units over 10 frames.
  - Has a cooldown.
- Light Attack:
  - Damage: 10
  - Short cooldown
- Heavy Attack:
  - Damage: 20
  - Long cooldown
- Attacks only hit if the opponent is inside the attack hitbox.

Each frame, the agent must output a dictionary with:
- move (left / right / None)
- attack (1 = light, 2 = heavy, None)
- jump (True / False)
- dash (left / right / None)
- debug
- saved_data

The agent must respond within 0.4 seconds per frame.

---

# AI Design (agent3.py)

## 1. Core Architecture

The final agent uses a combination of:

- Heuristic evaluation function
- Minimax algorithm with Alpha-Beta pruning
- Situation-based overrides (corner logic, anti-air, post-dash safety)

The AI balances aggression, positioning, and defensive reactions.

---

# Heuristic Function

The evaluation function estimates the quality of a game state using weighted factors:

### Main Factors:

1. **Health Difference**
   - Primary objective.
   - Higher HP advantage increases score.

2. **Distance to Opponent**
   - Encourages staying within effective attack range.
   - Penalizes excessive distance.

3. **Attack Cooldowns**
   - Rewards having attacks ready.
   - Penalizes long cooldown states.

4. **Opponent Attacking State**
   - Reduces score when staying inside opponent attack range during enemy attack.

5. **Airborne Detection**
   - Adjusts behavior when opponent is jumping.
   - Prevents unnecessary ground attacks.

The heuristic enables the agent to reason about positional advantage, risk, and offensive opportunity.

---

# Minimax with Alpha-Beta Pruning

The agent uses:

```
minimax_alpha_beta(state, depth, alpha, beta)
```

### Key Features:

- Depth-limited search (depth = 2)
- Alternating maximizing (self) and minimizing (opponent)
- Alpha-Beta pruning to reduce unnecessary branches
- Small, controlled action space to maintain performance under 0.4s limit

The opponent is modeled using the same action generator for adversarial reasoning.

---

# Additional Strategic Improvements

Beyond pure Minimax, the agent includes practical game intelligence:

### 1. Opening Dash Strategy
Safely closes distance at the beginning when far from opponent.

### 2. Corner Awareness
If near wall and opponent jumps, performs forward dash to reposition and avoid getting trapped.

### 3. Post-Dash Safety Buffer
After dashing forward, temporarily avoids attacking to prevent immediate punishment.

### 4. Heavy Attack Gating
Heavy attacks are only used when:
- Distance is appropriate
- Opponent is not airborne
- Risk is acceptable

### 5. Anti-Air Adjustments
Avoids ineffective ground attacks when opponent is airborne.

---

# Why agent3.py Is the Strongest Version

Compared to previous iterations, this version:

- Uses realistic hitbox simulation
- Avoids unsafe dash situations
- Handles wall positioning
- Reduces unnecessary whiff attacks
- Balances aggression and safety dynamically
- Performs consistently well against random agents

---

# Conclusion

This project demonstrates:

- Practical application of adversarial search (Minimax)
- Heuristic state evaluation design
- Real-time decision constraints
- Strategy refinement through iterative improvement

The final agent achieves strong and stable performance against a random opponent and represents the most optimized version developed during the project.

---

Author:  Mahan Baneshi
AI Project – Final Submission - winter 2025

