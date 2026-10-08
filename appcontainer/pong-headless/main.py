#!/usr/bin/env python3
"""Headless-Pong (ohne Display, Sandbox-tauglich).

JSON-Konfiguration von stdin; simuliert ein vollstaendiges Pong-Spiel mit zwei
KI-Schlaegern, rendert ausgewaehlte Frames als ASCII und schreibt Statistik nach
out/result.json sowie den Frame-Ablauf nach out/pong_replay.txt.
Nur Standardbibliothek.
"""

import json
import math
import os
import random
import sys

W = 100.0          # Spielfeldbreite
H = 60.0           # Spielfeldhoehe
PADDLE_W = 1.6     # Schlaegerdicke
PADDLE_H = 14.0    # Schlaegerhoehe
PADDLE_X = 3.0     # Schlaeger-Mitte, Abstand zur Wand
BALL_R = 1.2       # Ballradius
DT = 1.0 / 60.0    # Zeitschritt (60 Frames/s)
SERVE_SPEED = 60.0
MAX_BALL_SPEED = 320.0   # ab hier wird der Ball schneller, als die KI folgen kann
MIN_ANGLE = math.radians(13.0)   # Mindeststeigung, sonst endlose flache Rallys
SPEEDUP = 1.05


def clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


class Paddle:
    def __init__(self, x):
        self.x = x
        self.h = PADDLE_H
        self.speed = 70.0
        self.y = H / 2.0

    @property
    def top(self):
        return self.y - self.h / 2.0

    @property
    def bot(self):
        return self.y + self.h / 2.0

    def move_towards(self, ty, dt, gain=1.0):
        step = self.speed * gain * dt
        self.y += clamp(ty - self.y, -step, step)
        self.y = clamp(self.y, self.h / 2.0, H - self.h / 2.0)


class Game:
    def __init__(self, seed=7, max_points=11, max_steps=60000, difficulty=0.5,
                 left_err=3.0, left_gain=0.9,
                 right_err=6.0, right_gain=1.0, right_refresh=4):
        self.rng = random.Random(seed)
        self.max_points = max_points
        self.max_steps = max_steps
        # difficulty skaliert die Zielungenauigkeit beider KI-Schlaeger (0..1)
        self.difficulty = clamp(float(difficulty), 0.0, 1.0)
        self.left_err = left_err
        self.left_gain = left_gain
        self.right_err = right_err
        self.right_gain = right_gain
        self.right_refresh = max(1, int(right_refresh))

        self.pl = Paddle(PADDLE_X)
        self.pr = Paddle(W - PADDLE_X)
        self.pr_target = H / 2.0
        self.score = [0, 0]        # [links, rechts]
        self.steps = 0
        self.rallies = []          # Schlagwechsel je Punkt
        self.hits = 0              # Schlaegerkontakte insgesamt
        self.reversals = 0         # tatsaechliche Richtungsumkehrungen (Kontrolle)
        self.hits_in_rally = 0
        self.max_ball_speed = 0.0
        self.serve(to_left=bool(self.rng.getrandbits(1)))

    def serve(self, to_left):
        ang = self.rng.uniform(-0.35, 0.35)
        vx = -SERVE_SPEED if to_left else SERVE_SPEED
        self.ball = [W / 2.0, H / 2.0, vx, SERVE_SPEED * ang]
        self.hits_in_rally = 0

    def predict(self, bx, by, vx, vy, x_target, err=0.0):
        """Auftreffpunkt am Schlaeger inkl. Wandreflexionen, mit Fehler."""
        if abs(vx) < 1e-6:
            return H / 2.0
        t = (x_target - bx) / vx
        if t < 0:
            return H / 2.0
        y = by + vy * t
        span = H
        y %= 2.0 * span
        if y > span:
            y = 2.0 * span - y
        return clamp(y + self.rng.uniform(-err, err), BALL_R, H - BALL_R)

    def deflect(self, vx, vy, by, paddle):
        """Rueckwurf aus dem Auftreffpunkt. Die x-Richtung MUSS umkehren:
        Einfall von rechts (vx>0) -> Rueckwurf nach links (vx<0) und umgekehrt."""
        off = clamp((by - paddle.y) / (paddle.h / 2.0), -1.0, 1.0)
        speed = min(math.hypot(vx, vy) * SPEEDUP, MAX_BALL_SPEED)
        ang = off * math.radians(55.0)
        if abs(ang) < MIN_ANGLE:
            ang = MIN_ANGLE if ang >= 0.0 else -MIN_ANGLE
        sgn = -1.0 if vx > 0 else 1.0
        return sgn * speed * math.cos(ang), speed * math.sin(ang)

    def step(self):
        bx, by, vx, vy = self.ball
        vx_before = vx

        self.pl.move_towards(
            self.predict(bx, by, vx, vy, self.pl.x,
                         err=self.difficulty * self.left_err),
            DT, gain=self.left_gain)
        if self.steps % self.right_refresh == 0:
            self.pr_target = self.predict(bx, by, vx, vy, self.pr.x,
                                          err=self.difficulty * self.right_err)
        self.pr.move_towards(self.pr_target, DT, gain=self.right_gain)

        half = PADDLE_W / 2.0
        substeps = max(1, int(max(abs(vx), abs(vy)) * DT / 0.5) + 1)
        sdt = DT / substeps
        for _ in range(substeps):
            bx += vx * sdt
            by += vy * sdt

            if by - BALL_R < 0.0 and vy < 0.0:      # Decke
                by = BALL_R
                vy = -vy
            elif by + BALL_R > H and vy > 0.0:      # Boden
                by = H - BALL_R
                vy = -vy

            # linker Schlaeger: Ball kommt von rechts (vx<0)
            if vx < 0.0 and (bx - BALL_R) <= (self.pl.x + half) \
                    and (bx + BALL_R) >= (self.pl.x - half) \
                    and self.pl.top <= by <= self.pl.bot:
                bx = self.pl.x + half + BALL_R
                vx, vy = self.deflect(vx, vy, by, self.pl)
                self.hits_in_rally += 1
                self.hits += 1

            # rechter Schlaeger: Ball kommt von links (vx>0)
            if vx > 0.0 and (bx + BALL_R) >= (self.pr.x - half) \
                    and (bx - BALL_R) <= (self.pr.x + half) \
                    and self.pr.top <= by <= self.pr.bot:
                bx = self.pr.x - half - BALL_R
                vx, vy = self.deflect(vx, vy, by, self.pr)
                self.hits_in_rally += 1
                self.hits += 1

        # Kontrolle: bei einem Schlaegerkontakt muss das Vorzeichen von vx kippen
        if (vx > 0.0) != (vx_before > 0.0):
            self.reversals += 1

        self.ball = [bx, by, vx, vy]
        self.max_ball_speed = max(self.max_ball_speed, math.hypot(vx, vy))
        self.steps += 1

        if bx + BALL_R < 0.0:                 # Punkt fuer rechts
            self.score[1] += 1
            self.rallies.append(self.hits_in_rally)
            self.serve(to_left=True)          # Aufschlag zum Verlierer
        elif bx - BALL_R > W:                 # Punkt fuer links
            self.score[0] += 1
            self.rallies.append(self.hits_in_rally)
            self.serve(to_left=False)

    @property
    def finished(self):
        return max(self.score) >= self.max_points or self.steps >= self.max_steps


def render(game, cols=80, rows=24):
    grid = [[" "] * cols for _ in range(rows)]
    for c in range(cols):
        grid[0][c] = "-"
        grid[rows - 1][c] = "-"
    for r in range(1, rows - 1):
        if r % 2 == 1:
            grid[r][cols // 2] = ":"

    for pad in (game.pl, game.pr):
        c = int(pad.x / W * cols)
        top = int(round(pad.top / H * rows))
        bot = int(round(pad.bot / H * rows))
        for r in range(max(1, top), min(rows - 1, bot) + 1):
            grid[r][clamp(c, 0, cols - 1)] = "|"

    bx, by = game.ball[0], game.ball[1]
    c = clamp(int(bx / W * cols), 0, cols - 1)
    r = clamp(int(by / H * rows), 0, rows - 1)
    grid[r][c] = "o"
    return "\n".join("".join(row) for row in grid)


def read_config():
    try:
        raw = sys.stdin.read()
    except Exception:
        return {}
    if not raw or not raw.strip():
        return {}
    try:
        cfg = json.loads(raw)
        return cfg if isinstance(cfg, dict) else {}
    except ValueError:
        return {}


def main():
    cfg = read_config()
    seed = int(cfg.get("seed", 7))
    max_points = int(cfg.get("max_points", 11))
    difficulty = float(cfg.get("difficulty", 0.5))
    max_steps = int(cfg.get("max_steps", 60000))
    sample_every = max(1, int(cfg.get("sample_every", 300)))
    show_frames = max(1, int(cfg.get("show_frames", 3)))
    params = dict(difficulty=difficulty,
                  left_err=float(cfg.get("left_err", 3.0)),
                  left_gain=float(cfg.get("left_gain", 0.9)),
                  right_err=float(cfg.get("right_err", 6.0)),
                  right_gain=float(cfg.get("right_gain", 1.0)),
                  right_refresh=int(cfg.get("right_refresh", 4)))

    game = Game(seed=seed, max_points=max_points, max_steps=max_steps, **params)

    frames = []
    while not game.finished:
        game.step()
        if game.steps % sample_every == 0:
            frames.append((game.steps, list(game.score), render(game)))

    if game.score[0] > game.score[1]:
        winner = "links"
    elif game.score[1] > game.score[0]:
        winner = "rechts"
    else:
        winner = "unentschieden (Zeitlimit)"

    print("PONG (headless) - Seed %d, Difficulty %.2f, Ziel %d Punkte"
          % (seed, difficulty, max_points))
    print("Endstand links %d : %d rechts  -> %s"
          % (game.score[0], game.score[1], winner))
    print("Frames: %d (%.1f s simulierte Spielzeit), gespielte Punkte: %d"
          % (game.steps, game.steps * DT, len(game.rallies)))
    print("Schlaegerkontakte: %d, Richtungsumkehrungen: %d (muessen gleich sein)"
          % (game.hits, game.reversals))
    print("")
    if frames:
        picks = []
        for i in range(show_frames):
            idx = int(round(i * (len(frames) - 1) / max(1, show_frames - 1)))
            if idx not in picks:
                picks.append(idx)
        for idx in picks:
            st, sc, art = frames[idx]
            print("--- Frame %d   Stand links %d : %d rechts ---" % (st, sc[0], sc[1]))
            print(art)
            print("")

    rally_avg = (sum(game.rallies) / len(game.rallies)) if game.rallies else 0.0
    result = {
        "seed": seed,
        "parameters": params,
        "score": {"links": game.score[0], "rechts": game.score[1]},
        "winner": winner,
        "frames_simulated": game.steps,
        "simulated_seconds": round(game.steps * DT, 2),
        "points_played": len(game.rallies),
        "rally_hits": game.rallies,
        "rally_hits_avg": round(rally_avg, 2),
        "rally_hits_max": max(game.rallies) if game.rallies else 0,
        "paddle_hits": game.hits,
        "direction_reversals": game.reversals,
        "max_ball_speed": round(game.max_ball_speed, 1),
        "sampled_frames": len(frames),
    }

    out_dir = os.environ.get("LABAGENT_OUT_DIR", "out")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "result.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
    with open(os.path.join(out_dir, "pong_replay.txt"), "w", encoding="utf-8") as fh:
        for st, sc, art in frames:
            fh.write("--- Frame %d   Stand links %d : %d rechts ---\n" % (st, sc[0], sc[1]))
            fh.write(art + "\n\n")

    print("Statistik:", json.dumps(result["score"]), "| Punkte:", len(game.rallies),
          "| laengster Ballwechsel:", result["rally_hits_max"], "Schlaege")


if __name__ == "__main__":
    main()
