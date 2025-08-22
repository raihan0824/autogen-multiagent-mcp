# AutoGen MCP Multi-Agent Framework

A **completely generic** multi-agent framework using AutoGen with native MCP (Model Context Protocol) integration. Works with **ANY** MCP server - Kubernetes, PostgreSQL, AWS, GitHub, Monitoring, and more!

## 🌟 Key Features

✅ **100% Generic** - No hardcoded servers, tools, or commands  
✅ **Native AutoGen MCP** - Uses AutoGen's built-in MCP support with SSE transport  
✅ **Multi-Turn Tool Execution** - Intelligent tool retry, chaining, and failure handling  
✅ **Dynamic Tool Discovery** - Automatically discovers all available tools from any MCP server  
✅ **Multi-Server Support** - Connect to unlimited MCP servers simultaneously  
✅ **Flexible Tool Selection** - Use `*` for all tools or specify exact tools per server/agent  
✅ **Configuration-Driven** - Zero code changes needed, everything via JSON configs  
✅ **Dual-Level Filtering** - Control tools at both server and agent levels  
✅ **Intelligent Agent Conversations** - Multi-agent workflows with context preservation  

## 🚀 Installation Guide

### 1. Prerequisites
- Python 3.8+
- Access to an LLM API (OpenAI compatible)
- One or more running MCP servers with `/mcp-server/sse` endpoint

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
      "timeout_seconds": 30,
      "sse_endpoint": "/mcp-server/sse",
      "tools": ["*"]  // Use all available tools
    },
    {
      "name": "postgres", 
      "url": "http://localhost:3001",
      "enabled": true,
      "timeout_seconds": 30,
      "sse_endpoint": "/mcp-server/sse", 
      "tools": ["query_database", "list_tables"]  // Specific tools only
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
      "enabled": true,
      "type": "kubernetes",
      "description": "Kubernetes operations specialist",
      "capabilities": ["mcp", "kubernetes"],
      "mcp_servers": ["kubernetes"],
      "mcp_tools": ["*"],
      "system_message": "You are a Kubernetes Operations Specialist. Use your kubectl tools to help users manage Kubernetes clusters. When tools fail, try alternative approaches. Always explain what you're doing and what the results mean."
    },
    {
      "name": "reviewer",
      "enabled": true,
      "type": "reviewer", 
      "description": "Analysis and review specialist",
      "capabilities": ["data_analysis"],
      "system_message": "You analyze and review information provided by other agents, offering insights and recommendations."
    }
  ]
}
```

## 🔄 Multi-Agent Operation Flow

### 1. **Framework Initialization**
```
🔍 Framework starts → Connects to all enabled MCP servers via SSE
📡 Discovers available tools dynamically using AutoGen's native MCP support  
🎛️ Applies server-level tool filtering (*, specific tools, or none)
🤖 Creates agents with native AutoGen MCP tools and multi-turn capabilities
```

### 2. **Native Tool Execution**
```
👤 User: "check pods in mcp namespace and explain what you find"
🧠 AutoGen Agent decides: Uses kubectl_search tool automatically
🔧 AutoGen handles tool calling natively (no manual parsing needed)
🎯 Tool executes via MCP server with proper parameters
```

### 3. **Multi-Turn Conversation** 
```
📨 AutoGen manages SSE connection to MCP server
📊 Tool returns real data from Kubernetes cluster
🔄 Agent can retry with different tools if needed (kubectl_get, kubectl_describe, etc.)
🎉 Agent processes results and provides intelligent response
```

### 4. **Multi-Agent Workflow**
```
Agent Flow: kubernetes → reviewer

[1] 🤖 KUBERNETES: 
Uses kubectl_search tool → Gets detailed pod information
Explains pod status, distribution, and health

[2] 📋 REVIEWER: 
Analyzes the data comprehensively
Provides insights and actionable recommendations
Suggests monitoring, updates, and maintenance strategies
```

### 5. **Intelligent Tool Handling**
```
✅ Tool Success: Agent proceeds with analysis
❌ Tool Failure: Agent automatically tries alternative tools
🔄 Tool Chaining: Agent can use multiple tools in sequence
🧠 Context Preservation: Each agent sees full conversation history
```

## 🛠️ Usage Examples

### Basic Query
```bash
python main.py "check pods in mcp namespace"
```

### Override Agent Flow
```bash
AUTOGEN_CONVERSATION_FLOW='kubernetes' python main.py "show cluster overview"
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

### Agent Configuration
```json
{
  "name": "operations",
  "system_message": "You are an Operations Specialist. Use your available tools to help with infrastructure management. When tools fail, try alternative approaches and explain your reasoning.",
  "max_tool_iterations": 5,        // Allow up to 5 tool attempts
  "reflect_on_tool_use": true       // Agent reflects on tool results
}
```

## 🎪 Supported MCP Servers

The framework works with **ANY** MCP server that follows the standard protocol with SSE transport:

- **Kubernetes** - kubectl operations, cluster management
- **PostgreSQL** - Database queries, backups, monitoring  
- **AWS** - EC2, S3, Lambda operations
- **GitHub** - Repository management, CI/CD
- **Monitoring** - Prometheus, Grafana, alerting
- **Custom** - Any server implementing MCP protocol with `/mcp-server/sse` endpoint

## 🤖 Native AutoGen Tool Integration

### How It Works
Agents use AutoGen's native function calling - no manual command parsing needed:

1. **Agent Decision**: LLM automatically chooses appropriate tool
2. **Tool Execution**: AutoGen handles MCP server communication  
3. **Result Processing**: Agent analyzes results and can retry if needed
4. **Multi-Turn**: Agent can chain multiple tools or retry with alternatives

### Example Tool Flow
```
User: "Find failing pods and get their logs"

Agent Workflow:
1. Uses kubectl_search to find pods
2. If any failing pods found, uses kubectl_logs to get details  
3. If kubectl_logs fails, tries kubectl_describe as fallback
4. Analyzes all data and provides comprehensive response
```

## 🐛 Troubleshooting

### No agents found
- Check `agents.json` has `"enabled": true`
- Verify agents have appropriate capabilities configured
- Ensure MCP servers are reachable via SSE endpoints

### Tool not found
- Check MCP server is running with `/mcp-server/sse` endpoint
- Verify AutoGen can discover tools via native MCP integration
- Check server/agent tool filtering configuration

### Connection errors
- Verify MCP server URLs and SSE endpoints in `mcp_servers.json`
- Check network connectivity to MCP servers
- Ensure MCP servers support SSE transport

### Tool execution failures
- Agent will automatically retry with alternative tools
- Check agent logs for tool iteration attempts
- Verify MCP server responses are valid

## 📊 Example Output

```bash
$ python main.py "check pods in mcp namespace and explain what you find"

🚀 AutoGen MCP Framework
============================================================
✅ Configuration loaded and validated
✅ Agent orchestrator initialized
✅ CLI ready

🔍 Query: check pods in mcp namespace and explain what you find
--------------------------------------------------

🔄 Multi-Agent Conversation (2 agents participated):
================================================================================

[1] 🤖 KUBERNETES:
----------------------------------------
Using kubectl_search tool to find pods in mcp namespace...

✅ Found 9 pods in mcp namespace:
- elasticsearch-mcp-bridge-655cfd8d8d-dpnnz (Running)
- gitbook-mcp-bridge-567f9cdb99-jm6jb (Running)  
- kubernetes-host-jah-mcp-bridge-5db5d55cfb-rc4wg (Running)
- kubernetes-mgmt-mcp-bridge-96956c49b-g9v7r (Running)
- kubernetes-vclusterdev-mcp-bridge-887765b67-c6c4p (Running)
- kubernetes-vclusternim-mcp-bridge-6c4695cc46-nlm2h (Running)
- postgre-respona-dev-mcp-bridge-877f5c9c4-67h2b (Running)
- postgre-respona-prod-mcp-bridge-57cbbb68f7-cpbd9 (Running)
- respona-dashboard-mcp-bridge-5bf7c4878c-nln6p (Running)

All pods are distributed across multiple nodes and in Running state, 
indicating a healthy and well-balanced cluster deployment.

[2] 📋 REVIEWER:
----------------------------------------
Based on the Kubernetes data analysis:

**Insights:**
- All 9 pods are Running successfully (100% availability)
- Good node distribution across the cluster
- Mix of services: Elasticsearch, GitBook, PostgreSQL, dashboards
- Recent pod updates from June-August 2025

**Recommendations:**
- Monitor resource usage across nodes
- Implement automated health checks  
- Maintain regular security updates
- Consider backup strategies for critical services

================================================================================
✅ Workflow completed with 6 agent responses
```

## 🏗️ Key Dependencies

Current framework uses these core dependencies:

```txt
# AutoGen framework with native MCP support
autogen-agentchat[openai]>=0.7.3
autogen-ext[mcp]>=0.7.3

# Core dependencies
pydantic>=2.10.0
httpx>=0.28.1
python-dotenv>=1.0.0

# Development and testing  
pytest>=7.0.0
structlog>=23.0.0
```

No additional MCP dependencies needed - AutoGen handles everything natively!
Supports any standardized MCP server via SSE, Stdio, or HTTP transport.

## 🎉 Framework Capabilities

### ✅ **Multi-Turn Intelligence**
- **Tool Retry**: Agents automatically retry failed tools with alternatives
- **Tool Chaining**: Agents can use multiple tools in sequence to solve complex tasks
- **Context Preservation**: Full conversation history maintained across agent interactions
- **Smart Tool Selection**: LLM automatically chooses the most appropriate tool

### ✅ **Production Ready**
- **Zero Hardcoding**: Works with ANY MCP server out of the box
- **Dynamic Discovery**: Automatically finds and configures all available tools
- **Flexible Configuration**: Complete control via JSON files, no code changes needed
- **Robust Error Handling**: Graceful fallbacks and intelligent retry mechanisms

### ✅ **Enterprise Features**
- **Multi-Agent Workflows**: Sophisticated collaboration between specialized agents
- **Server Agnostic**: Support for unlimited concurrent MCP servers
- **Granular Tool Control**: Fine-grained filtering at server and agent levels
- **Native AutoGen Integration**: Leverages AutoGen's mature tooling ecosystem

### 🚀 **Get Started Now**

1. **Clone and install dependencies**
2. **Configure your MCP servers and agents** 
3. **Run your first query**
4. **Watch agents intelligently collaborate with tools!**

The framework is **completely generic** and **production-ready**! Add any MCP server, configure via JSON, and start automating complex workflows with intelligent multi-turn tool execution! 🚀 