# AutoGen MCP Multi-Agent Framework

A **completely generic** multi-agent framework using AutoGen with MCP (Model Context Protocol) integration. Works with **ANY** MCP server - Kubernetes, PostgreSQL, AWS, GitHub, Monitoring, and more!

## 🌟 Key Features

✅ **100% Generic** - No hardcoded servers, tools, or commands  
✅ **Dynamic Tool Discovery** - Automatically discovers all available tools from any MCP server  
✅ **Multi-Server Support** - Connect to unlimited MCP servers simultaneously  
✅ **Flexible Tool Selection** - Use `*` for all tools or specify exact tools per server/agent  
✅ **Configuration-Driven** - Zero code changes needed, everything via JSON configs  
✅ **Dual-Level Filtering** - Control tools at both server and agent levels  
✅ **Smart Parameter Parsing** - Handles various command formats generically  

## 🚀 Installation Guide

### 1. Prerequisites
- Python 3.8+
- Access to an LLM API (OpenAI compatible)
- One or more running MCP servers

### 2. Install Dependencies
```bash
git clone <your-repo>
cd autogen
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
# Create environment file
cat > .env << EOF
# LLM Configuration
LLM_MODEL=qwen/qwen25-72b-instruct
LLM_API_BASE=https://your-llm-api.com/v1
LLM_API_KEY=your-api-key-here

# Optional: Override conversation flow
# AUTOGEN_CONVERSATION_FLOW=kubernetes,security,reviewer
EOF
```

### 4. Configure MCP Servers
```json
// mcp_servers.json
{
  "servers": [
    {
      "name": "kubernetes",
      "url": "http://localhost:3000", 
      "enabled": true,
      "tools": ["*"]  // Use all available tools
    },
    {
      "name": "postgresql",
      "url": "http://localhost:3001",
      "enabled": true,
      "tools": ["pg_query", "pg_backup"]  // Only specific tools
    },
    {
      "name": "monitoring",
      "url": "http://localhost:3002", 
      "enabled": false  // Disabled server
    }
  ]
}
```

### 5. Configure Agents
```json
// agents.json  
{
  "agents": [
    {
      "name": "kubernetes",
      "agent_type": "custom",
      "enabled": true,
      "capabilities": ["mcp"],
      "mcp_servers": ["kubernetes"],
      "mcp_tools": ["*"],  // All tools from assigned servers
      "system_message": "You are an Operations Specialist. Use 'EXECUTE_MCP: [tool_name] [args]' format.",
      "allowed_namespaces": ["default", "mcp", "dev"]
    },
    {
      "name": "database",
      "agent_type": "custom", 
      "enabled": true,
      "capabilities": ["mcp"],
      "mcp_servers": ["postgresql"],
      "mcp_tools": ["pg_query", "pg_backup"],  // Only specific tools
      "system_message": "You are a Database Specialist. Use 'EXECUTE_MCP: [tool_name] [args]' format."
    }
  ]
}
```

## 🎯 Multi-Agent Operation Flow

### 1. **Tool Discovery Phase**
```
🔍 Framework starts → Connects to all enabled MCP servers
📡 Discovers available tools dynamically from each server  
🎛️ Applies server-level tool filtering (*, specific tools, or none)
🤖 Creates agents and applies agent-level tool filtering
```

### 2. **Query Processing**
```
👤 User: "get pods in mcp namespace"
🧠 LLM generates: "EXECUTE_MCP: kubectl_get pods -n mcp"
🔧 Framework parses command generically 
🎯 Maps tool to correct server dynamically
```

### 3. **Command Execution** 
```
📨 HTTP POST to MCP server: /mcp/tools/kubectl_get/call
📊 Parameters: {"resourceType": "pods", "namespace": "mcp"}
✅ Returns real data from Kubernetes cluster
🎉 Agent responds with formatted results
```

### 4. **Multi-Agent Conversation**
```
Agent Flow: kubernetes → security → reviewer

[1] 🤖 KUBERNETES: 
EXECUTE_MCP: kubectl_get pods -n mcp
✅ Found 5 running pods in mcp namespace

[2] 🛡️ SECURITY:
These pods look secure, all in expected namespace

[3] 📋 REVIEWER: 
Operation completed successfully, no issues found
```

## 🛠️ Usage Examples

### Basic Query
```bash
python main.py "get pods in default namespace"
```

### Override Agent Flow
```bash
AUTOGEN_CONVERSATION_FLOW='database' python main.py "show all tables"
```

### Interactive Mode
```bash
python main.py --interactive
```

## 🔧 Advanced Configuration

### Tool Selection Options

**Server Level (mcp_servers.json):**
```json
{
  "tools": ["*"]                    // All available tools
  "tools": ["tool1", "tool2"]       // Specific tools only  
  // No "tools" field              // Auto-discover all (same as *)
}
```

**Agent Level (agents.json):**
```json
{
  "mcp_tools": ["*"]                // All tools from assigned servers
  "mcp_tools": ["kubectl_get"]      // Only specific tools
  // No "mcp_tools" field          // All available tools
}
```

### Multiple Server Assignment
```json
{
  "name": "devops",
  "mcp_servers": ["kubernetes", "monitoring", "aws"],
  "mcp_tools": ["kubectl_get", "prometheus_query", "ec2_list"]
}
```

## 🎪 Supported MCP Servers

The framework works with **ANY** MCP server that follows the standard protocol:

- **Kubernetes** - kubectl operations, cluster management
- **PostgreSQL** - Database queries, backups, monitoring  
- **AWS** - EC2, S3, Lambda operations
- **GitHub** - Repository management, CI/CD
- **Monitoring** - Prometheus, Grafana, alerting
- **Custom** - Any server implementing MCP protocol

## 🚨 Command Format

Agents use this universal format for MCP commands:

```
EXECUTE_MCP: [tool_name] [arguments]

Examples:
EXECUTE_MCP: kubectl_get pods -n production
EXECUTE_MCP: pg_query SELECT * FROM users  
EXECUTE_MCP: ec2_list --region us-east-1
EXECUTE_MCP: prometheus_query up{job="api"}
```

## 🐛 Troubleshooting

### No agents found
- Check `agents.json` has `"enabled": true`
- Verify `"capabilities": ["mcp"]` is set
- Ensure MCP servers are reachable

### Tool not found
- Check MCP server is running and responsive
- Verify tool exists with: `curl http://localhost:3000/mcp/tools`
- Check server/agent tool filtering configuration

### Connection errors
- Verify MCP server URLs in `mcp_servers.json`
- Check network connectivity to MCP servers
- Ensure MCP servers are running and healthy

## 📊 Example Output

```bash
$ python main.py "get pods in mcp namespace"

🚀 AutoGen MCP Framework
============================================================
✅ Configuration loaded and validated
✅ MCP client created  
✅ Discovered 22 tools from kubernetes server
✅ Agent orchestrator initialized
✅ CLI ready

🔍 Query: get pods in mcp namespace
--------------------------------------------------

🔄 Multi-Agent Conversation (1 agents participated):
================================================================================

[1] 🤖 KUBERNETES:
----------------------------------------
EXECUTE_MCP: kubectl_get pods -n mcp

✅ Found 5 pods in mcp namespace:
- kubernetes-vclusterdev-mcp-bridge-887765b67-c6c4p (Running)
- kubernetes-vclusternim-mcp-bridge-6c4695cc46-nlm2h (Running)  
- postgre-respona-dev-mcp-bridge-877f5c9c4-67h2b (Running)
- postgre-respona-prod-mcp-bridge-57cbbb68f7-cpbd9 (Running)
- respona-dashboard-mcp-bridge-5bf7c4878c-nln6p (Running)

================================================================================
✅ Workflow completed with 1 agent responses
```

## 🎉 That's It!

The framework is **completely generic** and **production-ready**! Add any MCP server, configure via JSON, and start automating! No code changes ever needed! 🚀 