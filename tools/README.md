# Odysseus Custom Tools — RTS Hub Integration

This directory holds custom Open WebUI **Functions** for the RTS Hub deployment.
Functions are stored in the Odysseus database (not loaded from disk), so they
must be imported via the admin UI after each fresh database setup.

## Importing a Function

1. Open Odysseus at `https://<tailscale-host>:7000`
2. Sign in as admin
3. Go to **Admin → Workspace → Functions**
4. Click **[+] New Function**
5. Paste the contents of the `.py` file
6. Click **Save**

The function is now available to all models in the workspace.

---

## `rts_games_tool.py` — RTS Games Integration

Gives AI models live access to the RTS Chess and RTS Checkers game servers.

### Capabilities

| Tool call | What it does |
|-----------|-------------|
| `get_server_status()` | Check if Chess / Checkers / Odysseus servers are online |
| `get_chess_rules()` | Full RTS Chess mechanics reference (influence fields, LOCKED/DISABLED states, King-only capture, path interception, etc.) |
| `get_checkers_rules()` | Full RTS Checkers mechanics reference |
| `analyze_chess_position(description)` | Strategic analysis of a described board position |
| `monte_carlo_branch(game, position, branch_id, depth)` | Explore one MCTS branch |
| `aggregate_monte_carlo(branch_reports)` | Pick best move from branch evaluations |

### Configuring Valves

After importing, click the ⚙️ icon on the function to set:

| Valve | Default | Notes |
|-------|---------|-------|
| `HUB_STATUS_URL` | `http://localhost:8185/api/status` | Hub status API (internal) |
| `CHESS_HTTP_URL` | `http://localhost:8183` | RTS Chess HTTP server |
| `CHECKERS_HTTP_URL` | `http://localhost:8181` | RTS Checkers HTTP server |
| `CHESS_WS_PORT` | `7777` | RTS Chess WebSocket port |
| `CHECKERS_WS_PORT` | `7778` | RTS Checkers WebSocket port |

All defaults are correct for the standard dgx-spark deployment.

### Monte Carlo via Group Chat

1. In Odysseus, create a **Group Chat**
2. Add 3–4 model instances (e.g., 3× `qwen2.5:72b`)
3. Enable `rts_games_tool` for the chat
4. Prompt: *"Use monte_carlo_branch to explore Branch A / B / C for this position: [paste position]. Then aggregate_monte_carlo to pick the best move."*
5. Each model explores independently; the last model aggregates

This setup simulates parallel MCTS with the GPU running all branches simultaneously.
