# F5 Agent for Claude Code

An interactive Python agent that connects directly to F5 BIG-IP via iControl REST API for real-time monitoring and querying.

## Architecture

```
┌─────────────────┐    HTTPS/443     ┌─────────────────┐
│   F5 Agent      │ ◄─────────────► │   F5 BIG-IP     │
│                 │  iControl REST   │  172.16.10.10   │
│ ┌─────────────┐ │     API          │                 │
│ │ Interactive │ │                  │ ┌─────────────┐ │
│ │ CLI Thread  │ │                  │ │   Pools     │ │
│ └─────────────┘ │                  │ │   Members   │ │
│                 │                  │ │   Virtuals  │ │
│ ┌─────────────┐ │                  │ │   Logs      │ │
│ │ Background  │ │                  │ └─────────────┘ │
│ │ Monitor     │ │                  │                 │
│ │ (30s poll)  │ │                  │                 │
│ └─────────────┘ │                  │                 │
└─────────────────┘                  └─────────────────┘
        │
        ▼
┌─────────────────┐
│ Network Engineer│
│ Command Prompt  │
│                 │
│ > status        │
│ > pools         │ 
│ > summary       │
│ > quit          │
└─────────────────┘
```

## Features

- **Interactive CLI Interface** - Real-time command prompt for querying F5 state
- **Background Monitoring** - Continuous 30-second polling with state change alerts
- **Token-based Authentication** - Secure iControl REST API access
- **Multi-threaded Design** - Monitor and interact simultaneously
- **Real-time State Detection** - Instant alerts when pool members change state
- **Comprehensive Querying** - Pools, virtual servers, logs, and health summaries

## Setup

1. Create and activate a virtual environment:
```bash
# Create virtual environment
python3 -m venv f5-agent-env

# Activate virtual environment (macOS/Linux)
source f5-agent-env/bin/activate

# Activate virtual environment (Windows)
f5-agent-env\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure your F5 credentials in `f5_agent.py`:
```python
F5_HOST = "172.16.10.10"
F5_USERNAME = "admin" 
F5_PASSWORD = "W3lcome098!"
```

## Usage

Run the agent:
```bash
python f5_agent.py
```

The agent will:
- Connect to F5 management interface at https://172.16.10.10
- Authenticate using token-based auth
- Start interactive command interface
- Monitor pool member states in background
- Allow real-time queries and state inspection

## Interactive Commands

Once running, you can use these commands:

- `help` - Show available commands
- `status` - Show overall F5 connection status
- `pools` - List all pools and member states  
- `pool <name>` - Show detailed info for specific pool
- `virtual` - Show virtual servers and their status
- `logs` - Show recent system logs
- `summary` - Show health summary with percentages
- `quit` - Exit the agent

The agent continuously monitors in the background and will alert you to any pool member state changes.

## Example Session

```bash
$ python f5_agent.py
[2025-08-20 10:30:15] Starting F5 Interactive Agent
[2025-08-20 10:30:15] Target: 172.16.10.10
Type 'help' for commands or 'quit' to exit
------------------------------------------------------------
[2025-08-20 10:30:15] Authentication successful

> status
F5 Status for 172.16.10.10:
Connected: Yes
Last updated: 2025-08-20 10:30:20
Pool members: 8 total, 6 up, 2 down

> pools
Pool Status:
  web_pool: 3/4 members up
    ✓ web1 (10.1.1.10) - up
    ✓ web2 (10.1.1.11) - up  
    ✓ web3 (10.1.1.12) - up
    ✗ web4 (10.1.1.13) - down
  
  api_pool: 3/4 members up
    ✓ api1 (10.1.2.10) - up
    ✓ api2 (10.1.2.11) - up
    ✓ api3 (10.1.2.12) - up
    ✗ api4 (10.1.2.13) - down

> summary
F5 Health Summary for 172.16.10.10:
Overall Health: 75.0%
Pool Members: 6/8 operational

Members DOWN:
  ✗ web_pool/web4 (10.1.1.13)
  ✗ api_pool/api4 (10.1.2.13)

Virtual Servers: 4/4 enabled
Last Check: 2025-08-20 10:30:25

> pool web_pool
Pool 'web_pool' Details:
  Member: web1
    Address: 10.1.1.10
    State: up
    Session: enabled
    Connection Limit: 1000

  Member: web2  
    Address: 10.1.1.11
    State: up
    Session: enabled
    Connection Limit: 1000

[2025-08-20 10:31:22] STATE CHANGE: web_pool/web4 down -> up
> 
Pool 'web_pool' now 4/4 members up!

> quit
Goodbye!
```

## Data Flow

1. **Authentication** - Agent authenticates with F5 using admin credentials
2. **Background Thread** - Starts continuous monitoring (30s intervals)
3. **Interactive Thread** - Waits for user commands at prompt
4. **API Calls** - Each command triggers specific iControl REST endpoints:
   - `status` → `/mgmt/tm/ltm/pool` (member counts)
   - `pools` → `/mgmt/tm/ltm/pool` + `/mgmt/tm/ltm/pool/{name}/members`
   - `virtual` → `/mgmt/tm/ltm/virtual`
   - `logs` → `/mgmt/tm/sys/log`
5. **State Tracking** - Background thread compares states and alerts on changes
6. **Real-time Updates** - State changes interrupt user prompt immediately

## Advantages

- Real-time data access
- Can get more than just logs (stats, config, etc.)
- Can take actions (disable pool members, etc.)
- Direct API access without intermediate systems