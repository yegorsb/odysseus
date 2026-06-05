"""
RTS Games Tool — Open WebUI Function
=====================================
Install in Odysseus:
  Admin → Workspace → Functions → [+] New Function → paste this file → Save

Gives AI models access to the RTS game servers so they can:
  • Check whether Chess / Checkers servers are online
  • Describe current game rules and mechanics for analysis
  • Query active game rooms
  • Accept a board state (as text/JSON) and provide strategic analysis
  • Coordinate Monte Carlo tree search across a group chat

Monte Carlo setup:
  In Odysseus, create a Group Chat with 3-4 model instances and enable this
  Function.  Each model explores a different branch and reports evaluation
  scores back to the group.  The "orchestrator" message declares the winner.

Configuration (edit the Valves below to match your deployment):
  HUB_URL   — internal URL of the hub status API (default: http://localhost:8185)
  CHESS_WS_PORT / CHECKERS_WS_PORT — used to construct WebSocket addresses
"""

import json
import urllib.request
import urllib.error
from pydantic import BaseModel, Field


# ── Valves (admin-configurable in Odysseus UI) ────────────────────────────────

class Valves(BaseModel):
    HUB_STATUS_URL: str = Field(
        default="http://localhost:8185/api/status",
        description="Internal URL to the hub status.py health endpoint.",
    )
    CHESS_HTTP_URL: str = Field(
        default="http://localhost:8183",
        description="Internal HTTP URL for the RTS Chess game server.",
    )
    CHECKERS_HTTP_URL: str = Field(
        default="http://localhost:8181",
        description="Internal HTTP URL for the RTS Checkers game server.",
    )
    CHESS_WS_PORT: int = Field(
        default=7777,
        description="WebSocket port for RTS Chess Godot server.",
    )
    CHECKERS_WS_PORT: int = Field(
        default=7778,
        description="WebSocket port for RTS Checkers Godot server.",
    )
    TIMEOUT_SECONDS: float = Field(
        default=2.0,
        description="HTTP request timeout in seconds.",
    )


# ── Tool class ────────────────────────────────────────────────────────────────

class Tools:
    def __init__(self):
        self.valves = Valves()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get(self, url: str) -> dict | None:
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=self.valves.TIMEOUT_SECONDS) as resp:
                return json.loads(resp.read())
        except Exception:
            return None

    # ── Public tools ──────────────────────────────────────────────────────────

    def get_server_status(self) -> str:
        """
        Check whether the RTS Chess, RTS Checkers, and Odysseus servers are
        currently online.  Returns a plain-text summary.
        """
        data = self._get(self.valves.HUB_STATUS_URL)
        if data is None:
            return "Could not reach the hub status API. The hub may be offline."

        lines = ["RTS Game Server Status", "=" * 30]
        for name, info in data.items():
            if name == "odysseus":
                state = "online" if info.get("ui") else "offline"
                lines.append(f"Odysseus  : {state}")
            else:
                ws   = "✓" if info.get("ws")   else "✗"
                http = "✓" if info.get("http") else "✗"
                both = info.get("ws") and info.get("http")
                state = "online" if both else ("partial" if info.get("ws") else "offline")
                lines.append(f"{name.capitalize():<10}: {state}  (WS {ws}  HTTP {http})")
        return "\n".join(lines)

    def get_chess_rules(self) -> str:
        """
        Return a concise description of the RTS Chess game mechanics.
        Use this when planning strategy, tutoring a player, or setting up a
        Monte Carlo simulation.
        """
        return """
RTS CHESS — GAME MECHANICS REFERENCE
======================================

This is NOT standard chess. Key differences:

INFLUENCE FIELDS
  Each piece projects an influence field (BFS, radius = influence_range).
  Blocked by occupied tiles unless the piece has through-flags set.
  Incoming influence from each opponent is summed per piece.

PIECE STATES
  ACTIVE    — can move, projects full influence
  LOCKED    — two pieces have equal mutual influence; neither can move,
               but both still project
  DISABLED  — incoming influence > own influence_range; cannot move AND
               cannot project (effectively "frozen")
  CAPTURED  — removed from board

ONLY THE KING CAN CAPTURE
  A King may move onto a DISABLED enemy piece to capture it.
  The King itself must not be under any opposing influence when it captures.

WIN CONDITION
  Capture the enemy King.

MOVEMENT
  BFS within move_range steps.
  PATH INTERCEPTION: a piece stops mid-path if any tile in its route would
  LOCK or DISABLE it.

SPECIAL PIECES
  Knight  — move_through_friendly = true, move_through_enemy = true
             (jumps over all pieces, cannot be intercepted mid-path)
  Bishop  — vision_through_friendly = true, vision_through_enemy = true

SQUAD MOVES
  Tight formations can move as a unit (one compass step per activation).

FOG OF WAR
  Each piece has vision_range. Hidden enemies still project influence.

OSCILLATION RESOLUTION
  3-pass detection; paradoxes resolved by local force-based split.

BOARD TYPES
  Square   — 8×8, starting layout: Knight-King-Knight + 4 Pawns per side
  Triangle — 14×10, full piece set

MODES
  Turn-based  — alternating moves with full deliberation time
  RTS         — simultaneous moves, per-piece cooldown timers
""".strip()

    def get_checkers_rules(self) -> str:
        """
        Return a concise description of the RTS Checkers game mechanics.
        """
        return """
RTS CHECKERS — GAME MECHANICS REFERENCE
=========================================

Standard 8×8 draughts rules plus RTS extensions.

STANDARD RULES
  • Pieces move diagonally forward only (kings move in all directions)
  • Captures are mandatory; multi-jump chains must be completed
  • A piece reaching the far rank is kinged

RTS MODE EXTENSIONS
  • Both players submit moves simultaneously
  • No waiting for opponent — real-time race to capture
  • Move cooldown per piece prevents instant spam

AI LEARNING
  • Each completed game exports a replay
  • Replays are sent to the DGX Spark GPU server for Monte Carlo training
  • Trained weights are hot-loaded before the next game
""".strip()

    def analyze_chess_position(self, board_state_description: str) -> str:
        """
        Analyze a described RTS Chess board position and suggest the best
        strategic action.

        Args:
            board_state_description: Natural language or structured description
                of piece positions, their states (ACTIVE/LOCKED/DISABLED), and
                current influence projections.

        Returns strategic analysis including: threats, influence control,
        recommended moves, and win conditions.
        """
        # The actual analysis is performed by the LLM using the rules context
        # injected below.  This function packages the prompt context.
        rules = self.get_chess_rules()
        return (
            f"{rules}\n\n"
            "--- POSITION TO ANALYZE ---\n"
            f"{board_state_description}\n\n"
            "Analyze this position using the mechanics above:\n"
            "1. Which pieces are LOCKED or DISABLED and why?\n"
            "2. Who has influence dominance over the center?\n"
            "3. Can any King make a capture this turn?\n"
            "4. What is the most forcing sequence of moves?\n"
            "5. Monte Carlo evaluation: estimate win probability for each player."
        )

    def monte_carlo_branch(
        self,
        game: str,
        position_description: str,
        branch_id: str,
        depth: int = 3,
    ) -> str:
        """
        Explore one branch of a Monte Carlo tree for the given game position.
        Use this in a Group Chat where each model instance receives a different
        branch_id and explores independently.

        Args:
            game: "chess" or "checkers"
            position_description: Current board state (text description or JSON).
            branch_id: Label for this branch (e.g. "A", "B", "C").
                Each model in the group chat should receive a unique branch_id.
            depth: How many half-moves deep to explore (default 3).

        Returns a branch evaluation: move sequence, resulting position, and
        a win-probability score between 0.0 (certain loss) and 1.0 (certain win).
        """
        rules = self.get_chess_rules() if game == "chess" else self.get_checkers_rules()
        return (
            f"{rules}\n\n"
            f"MONTE CARLO BRANCH EXPLORATION — Branch {branch_id}\n"
            f"Depth: {depth} half-moves\n\n"
            f"Starting position:\n{position_description}\n\n"
            f"Instructions for Branch {branch_id}:\n"
            f"1. Choose a promising move sequence to explore (different from other branches).\n"
            f"2. Play out {depth} half-moves, alternating sides.\n"
            f"3. Evaluate the resulting position.\n"
            f"4. Report: move_sequence, final_position_summary, win_probability (0.0–1.0)\n\n"
            f"Format your response as:\n"
            f"BRANCH: {branch_id}\n"
            f"MOVES: [move1, move2, ...]\n"
            f"RESULT: <position description>\n"
            f"SCORE: <float 0.0–1.0 for the side that moved first>\n"
            f"REASONING: <brief justification>"
        )

    def aggregate_monte_carlo(self, branch_reports: str) -> str:
        """
        Aggregate branch evaluation reports from a Monte Carlo group chat
        session and declare the best move.

        Args:
            branch_reports: Concatenated output from all Branch models in the
                group chat (each starting with 'BRANCH: X').

        Returns the best move, average score, and confidence.
        """
        return (
            "MONTE CARLO AGGREGATION\n"
            "=======================\n\n"
            "Branch reports received:\n"
            f"{branch_reports}\n\n"
            "Instructions:\n"
            "1. Parse each BRANCH / MOVES / SCORE block above.\n"
            "2. Average the scores for each unique first move.\n"
            "3. Select the first move with the highest average score.\n"
            "4. Report:\n"
            "   BEST_MOVE: <move>\n"
            "   AVG_SCORE: <float>\n"
            "   CONFIDENCE: <low|medium|high> based on variance across branches\n"
            "   BRANCHES_SAMPLED: <count>\n"
            "   SUMMARY: <one sentence justification>"
        )
