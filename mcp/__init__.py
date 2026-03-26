"""
STARK MCP (Model Context Protocol) Module
==========================================
Implements MCP server and client for STARK integration.

This module provides:
- MCP Server: Exposes STARK capabilities (agents, tools, resources)
- MCP Client: Access external MCP servers and tools
- MCP Agent: Orchestrates external tool usage via MCP

Architecture:
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   STARK Core    │◄──►│   MCP Server     │◄──►│  External Apps  │
│  (Agents, etc)  │    │ (expose tools)   │    │   (via MCP)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   MCP Client    │◄──►│  External MCP    │◄──►│  External Tools │
│ (access tools)  │    │    Servers       │    │ (filesystem, etc)│
└─────────────────┘    └──────────────────┘    └─────────────────┘

Module 8 of 9 - External Integration
"""

# =============================================================================
# IMPORTS
# =============================================================================

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


from core.constants import (
    MCP_CLIENT_ENABLED,
    MCP_CLIENT_TIMEOUT_SECONDS,
    MCP_MAX_EXTERNAL_SERVERS,
    MCP_RESOURCE_TYPES,
    MCP_SERVER_ENABLED,
    MCP_SERVER_HOST,
    MCP_SERVER_NAME,
    MCP_SERVER_PORT,
    MCP_SERVER_VERSION,
    MCP_TOOL_CATEGORIES,
    PROJECT_ROOT,
)
from utils.logger import get_logger

# =============================================================================
# LOGGER
# =============================================================================

logger = get_logger(__name__)

# =============================================================================
# MCP SERVER IMPLEMENTATION
# =============================================================================

class STARKMCPServer:
    """
    MCP Server that exposes STARK capabilities to external applications.
    
    Provides:
    - Tools: Access to STARK agents (code, file, web, etc.)
    - Resources: System information, logs, memory, adapters
    - Prompts: Pre-configured prompts for common tasks
    """
    
    def __init__(self):
        """Initialize MCP server."""
        from mcp.server.fastmcp import FastMCP
        self.server = FastMCP(MCP_SERVER_NAME)
        self._setup_tools()
        self._setup_resources()
        self._setup_prompts()
        self._running = False
        
    def _setup_tools(self):
        """Setup MCP tools that expose STARK agent capabilities."""
        
        @self.server.tool()
        def stark_query(query: str, task_type: Optional[str] = None) -> str:
            """
            Execute a STARK query using the intelligent routing system.
            
            Args:
                query: Natural language query or task
                task_type: Optional task type hint (conversation, code_generation, etc.)
                
            Returns:
                STARK response with routing information
            """
            from core.main import STARK
            
            try:
                start_time = time.time()
                result = STARK.process_query(query, task_type_hint=task_type)
                elapsed_ms = (time.time() - start_time) * 1000
                
                response = {
                    "query": query,
                    "task_type": result.get("task", "unknown"),
                    "confidence": result.get("confidence", 0.0),
                    "response": result.get("response", ""),
                    "model": result.get("model", "unknown"),
                    "routing_method": result.get("routing_method", "unknown"),
                    "latency_ms": round(elapsed_ms, 2),
                    "memory_stored": result.get("memory_stored", False),
                }
                
                logger.info(f"MCP tool 'stark_query' completed in {elapsed_ms:.2f}ms")
                return json.dumps(response, indent=2)
                
            except Exception as e:
                logger.error(f"STARK query failed: {e}", exc_info=True)
                return json.dumps({
                    "error": str(e),
                    "query": query,
                    "success": False
                })
        
        @self.server.tool()
        def stark_code_generate(prompt: str, language: str = "python") -> str:
            """
            Generate code using STARK's code generation agent.
            
            Args:
                prompt: Code generation prompt
                language: Target programming language
                
            Returns:
                Generated code with metadata
            """
            from agents.code_agent import CodeAgent
            
            try:
                agent = CodeAgent()
                full_prompt = f"Generate {language} code: {prompt}"
                result = agent.execute(full_prompt, {"language": language})
                
                response = {
                    "code": result.output,
                    "language": language,
                    "success": result.success,
                    "execution_time_ms": result.execution_time_ms,
                    "steps_taken": result.steps_taken,
                }
                
                if not result.success:
                    response["error"] = result.error
                
                logger.info(f"MCP tool 'stark_code_generate' completed")
                return json.dumps(response, indent=2)
                
            except Exception as e:
                logger.error(f"Code generation failed: {e}", exc_info=True)
                return json.dumps({
                    "error": str(e),
                    "success": False
                })
        
        @self.server.tool()
        def stark_file_read(file_path: str) -> str:
            """
            Read file content using STARK's file agent with safety checks.
            
            Args:
                file_path: Path to file to read
                
            Returns:
                File content with metadata
            """
            from agents.file_agent import FileAgent
            
            try:
                agent = FileAgent()
                result = agent.execute("read_file", {"file_path": file_path})
                
                response = {
                    "content": result.output,
                    "file_path": file_path,
                    "success": result.success,
                    "execution_time_ms": result.execution_time_ms,
                }
                
                if not result.success:
                    response["error"] = result.error
                
                logger.info(f"MCP tool 'stark_file_read' completed")
                return json.dumps(response, indent=2)
                
            except Exception as e:
                logger.error(f"File read failed: {e}", exc_info=True)
                return json.dumps({
                    "error": str(e),
                    "success": False
                })
        
        @self.server.tool()
        def stark_web_scrape(url: str, selector: Optional[str] = None) -> str:
            """
            Scrape web content using STARK's web agent.
            
            Args:
                url: URL to scrape
                selector: Optional CSS selector for specific content
                
            Returns:
                Scraped content with metadata
            """
            from agents.web_agent import WebAgent
            
            try:
                agent = WebAgent()
                context = {"url": url}
                if selector:
                    context["selector"] = selector
                    
                result = agent.execute("scrape", context)
                
                response = {
                    "content": result.output,
                    "url": url,
                    "success": result.success,
                    "execution_time_ms": result.execution_time_ms,
                }
                
                if not result.success:
                    response["error"] = result.error
                
                logger.info(f"MCP tool 'stark_web_scrape' completed")
                return json.dumps(response, indent=2)
                
            except Exception as e:
                logger.error(f"Web scrape failed: {e}", exc_info=True)
                return json.dumps({
                    "error": str(e),
                    "success": False
                })
        
        @self.server.tool()
        def stark_memory_recall(query: str, top_k: int = 5) -> str:
            """
            Recall memories from STARK's neuromorphic memory.
            
            Args:
                query: Query for memory recall
                top_k: Number of memories to return
                
            Returns:
                Recalled memories with relevance scores
            """
            from memory.neuromorphic_memory import NeuromorphicMemory
            
            try:
                memory = NeuromorphicMemory()
                memories = memory.recall(query, top_k=top_k)
                
                response = {
                    "query": query,
                    "memories": [
                        {
                            "content": mem.content,
                            "relevance": mem.activation,
                            "created": mem.timestamp,
                            "access_count": mem.access_count,
                        }
                        for mem in memories
                    ],
                    "total_memories": len(memories),
                }
                
                logger.info(f"MCP tool 'stark_memory_recall' completed")
                return json.dumps(response, indent=2)
                
            except Exception as e:
                logger.error(f"Memory recall failed: {e}", exc_info=True)
                return json.dumps({
                    "error": str(e),
                    "success": False
                })
    
    def _setup_resources(self):
        """Setup MCP resources for system information."""
        
        @self.server.resource("stark://config")
        def get_config() -> str:
            """Get STARK system configuration."""
            from core.config import get_config
            
            try:
                config = get_config()
                return json.dumps({
                    "model_name": config.model_name,
                    "log_level": config.log_level,
                    "max_length": config.max_length,
                    "lora_rank": config.lora_rank,
                    "memory_enabled": config.memory_enabled,
                    "learning_enabled": config.learning_enabled,
                }, indent=2)
            except Exception as e:
                return json.dumps({"error": str(e)})
        
        @self.server.resource("stark://stats")
        def get_stats() -> str:
            """Get STARK system statistics."""
            try:
                from core.main import STARK
                
                stats = {
                    "version": MCP_SERVER_VERSION,
                    "uptime_seconds": time.time() - STARK.start_time,
                    "total_queries": STARK.stats.get("total_queries", 0),
                    "avg_latency_ms": STARK.stats.get("avg_latency_ms", 0),
                    "active_adapters": len(STARK.adapter_manager.active_adapters),
                    "memory_nodes": STARK.memory.node_count,
                    "system_health": STARK.health_monitor.get_status(),
                }
                
                return json.dumps(stats, indent=2)
            except Exception as e:
                return json.dumps({"error": str(e)})
        
        @self.server.resource("stark://agents")
        def get_agents() -> str:
            """Get available STARK agents and their capabilities."""
            try:
                from agents.base_agent import AgentOrchestrator
                
                orchestrator = AgentOrchestrator()
                agents = []
                
                for agent_name, agent in orchestrator.agents.items():
                    agents.append({
                        "name": agent_name,
                        "type": agent.agent_type.value,
                        "description": agent.description,
                        "status": agent.status.value,
                        "timeout": agent.timeout,
                    })
                
                return json.dumps({"agents": agents}, indent=2)
            except Exception as e:
                return json.dumps({"error": str(e)})
    
    def _setup_prompts(self):
        """Setup MCP prompts for common STARK tasks."""
        
        @self.server.prompt()
        def code_review_prompt() -> str:
            """Get prompt template for code review tasks."""
            return """
            Please review the following code for:
            1. Security vulnerabilities
            2. Performance issues
            3. Code style and best practices
            4. Potential bugs
            5. Documentation improvements
            
            Provide specific, actionable feedback with examples.
            """
        
        @self.server.prompt()
        def debug_prompt() -> str:
            """Get prompt template for debugging tasks."""
            return """
            Please help debug this issue by:
            1. Analyzing the error message and stack trace
            2. Identifying the root cause
            3. Suggesting specific fixes
            4. Explaining why the issue occurred
            5. Providing prevention strategies
            
            Be thorough and provide code examples where helpful.
            """
        
        @self.server.prompt()
        def optimization_prompt() -> str:
            """Get prompt template for optimization tasks."""
            return """
            Please optimize this code for:
            1. Performance (speed and memory usage)
            2. Readability and maintainability
            3. Scalability
            4. Resource efficiency
            
            Provide before/after comparisons and explain the improvements.
            """
    
    async def start(self):
        """Start the MCP server."""
        if not MCP_SERVER_ENABLED:
            logger.info("MCP server disabled in configuration")
            return
            
        try:
            logger.info(f"Starting MCP server on {MCP_SERVER_HOST}:{MCP_SERVER_PORT}")
            self._running = True
            
            # Run server using stdio transport
            await self.server.run()
            
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}", exc_info=True)
            raise
    
    def stop(self):
        """Stop the MCP server."""
        self._running = False
        logger.info("MCP server stopped")

# =============================================================================
# MCP CLIENT IMPLEMENTATION
# =============================================================================

class STARKMCPClient:
    """
    MCP Client that connects to external MCP servers to access their tools.
    
    Allows STARK to use external tools and resources via MCP protocol.
    """
    
    def __init__(self):
        """Initialize MCP client."""
        self.connections: Dict[str, Any] = {}
        self.available_servers: Dict[str, Dict] = {}
        self._max_servers = MCP_MAX_EXTERNAL_SERVERS
        
    async def connect_server(self, 
                           server_id: str, 
                           command: str, 
                           args: Optional[List[str]] = None,
                           env: Optional[Dict[str, str]] = None) -> bool:
        """
        Connect to an external MCP server.
        
        Args:
            server_id: Unique identifier for the server
            command: Command to start the server
            args: Command arguments
            env: Environment variables
            
        Returns:
            True if connection successful
        """
        if not MCP_CLIENT_ENABLED:
            logger.info("MCP client disabled in configuration")
            return False
            
        if len(self.connections) >= self._max_servers:
            logger.warning(f"Maximum MCP servers ({self._max_servers}) reached")
            return False
            
        try:
            from mcp.client.stdio import StdioServerParameters, stdio_client
            from mcp.client.session import ClientSession

            server_params = StdioServerParameters(
                command=command,
                args=args or [],
                env=env
            )

            # Create stdio client connection
            (read, write) = await stdio_client(server_params).__aenter__()

            # Create client session
            session = ClientSession(read, write)
            await session.initialize()
            
            # Store connection
            self.connections[server_id] = {
                "session": session,
                "read": read,
                "write": write,
                "params": server_params,
            }
            
            # Get server capabilities
            tools = await session.list_tools()
            resources = await session.list_resources()
            prompts = await session.list_prompts()
            
            self.available_servers[server_id] = {
                "tools": [tool.name for tool in tools.tools],
                "resources": [resource.uri for resource in resources.resources],
                "prompts": [prompt.name for prompt in prompts.prompts],
                "connected_at": time.time(),
            }
            
            logger.info(f"Connected to MCP server '{server_id}' with {len(tools.tools)} tools")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server '{server_id}': {e}", exc_info=True)
            return False
    
    async def disconnect_server(self, server_id: str) -> bool:
        """
        Disconnect from an external MCP server.
        
        Args:
            server_id: Server identifier
            
        Returns:
            True if disconnection successful
        """
        if server_id not in self.connections:
            logger.warning(f"Server '{server_id}' not connected")
            return False
            
        try:
            connection = self.connections[server_id]
            
            # Close session and streams
            await connection["session"].__aexit__(None, None, None)
            await connection["read"].aclose()
            await connection["write"].aclose()
            
            # Remove from tracking
            del self.connections[server_id]
            del self.available_servers[server_id]
            
            logger.info(f"Disconnected from MCP server '{server_id}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to disconnect from MCP server '{server_id}': {e}", exc_info=True)
            return False
    
    async def call_tool(self, 
                       server_id: str, 
                       tool_name: str, 
                       arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Call a tool on an external MCP server.
        
        Args:
            server_id: Server identifier
            tool_name: Tool name to call
            arguments: Tool arguments
            
        Returns:
            Tool result
        """
        if server_id not in self.connections:
            return {"error": f"Server '{server_id}' not connected"}
            
        try:
            session = self.connections[server_id]["session"]
            result = await session.call_tool(tool_name, arguments or {})
            
            # Convert result to serializable format
            response = {
                "success": not result.isError,
                "content": [],
                "server_id": server_id,
                "tool_name": tool_name,
            }
            
            from mcp.types import TextContent
            for content in result.content:
                if isinstance(content, TextContent):
                    response["content"].append({
                        "type": "text",
                        "text": content.text
                    })
                # Handle other content types as needed
            
            logger.debug(f"Called tool '{tool_name}' on server '{server_id}'")
            return response
            
        except Exception as e:
            logger.error(f"Failed to call tool '{tool_name}' on server '{server_id}': {e}", exc_info=True)
            return {
                "error": str(e),
                "success": False,
                "server_id": server_id,
                "tool_name": tool_name
            }
    
    async def read_resource(self, server_id: str, uri: str) -> Dict[str, Any]:
        """
        Read a resource from an external MCP server.
        
        Args:
            server_id: Server identifier
            uri: Resource URI
            
        Returns:
            Resource content
        """
        if server_id not in self.connections:
            return {"error": f"Server '{server_id}' not connected"}
            
        try:
            session = self.connections[server_id]["session"]
            content, mime_type = await session.read_resource(uri)
            
            response = {
                "success": True,
                "content": content,
                "mime_type": mime_type,
                "server_id": server_id,
                "uri": uri,
            }
            
            logger.debug(f"Read resource '{uri}' from server '{server_id}'")
            return response
            
        except Exception as e:
            logger.error(f"Failed to read resource '{uri}' from server '{server_id}': {e}", exc_info=True)
            return {
                "error": str(e),
                "success": False,
                "server_id": server_id,
                "uri": uri
            }
    
    def list_available_tools(self, server_id: Optional[str] = None) -> Dict[str, List[str]]:
        """
        List available tools from connected servers.
        
        Args:
            server_id: Optional server ID to filter by
            
        Returns:
            Dictionary of server_id -> list of tool names
        """
        if server_id:
            if server_id in self.available_servers:
                return {server_id: self.available_servers[server_id]["tools"]}
            else:
                return {}
        else:
            return {
                sid: info["tools"] 
                for sid, info in self.available_servers.items()
            }
    
    def get_server_info(self, server_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a connected server.
        
        Args:
            server_id: Server identifier
            
        Returns:
            Server information or None if not found
        """
        return self.available_servers.get(server_id)

# =============================================================================
# MCP AGENT IMPLEMENTATION
# =============================================================================

class MCPAgent:
    """
    Agent that orchestrates external tool usage via MCP protocol.
    
    Intelligently selects and uses tools from external MCP servers
    to enhance STARK's capabilities.
    """
    
    def __init__(self, name: str = "MCPAgent"):
        """Initialize MCP agent."""
        from agents.base_agent import BaseAgent, AgentType, AgentResult
        
        self.name = name
        self.client = STARKMCPClient()
        self._initialized = False
    
    async def initialize(self):
        """Initialize MCP client and connect to default servers."""
        if self._initialized:
            return
            
        # Connect to common MCP servers if available
        await self._connect_default_servers()
        self._initialized = True
        logger.info("MCP Agent initialized")
    
    async def _connect_default_servers(self):
        """Connect to commonly available MCP servers."""
        default_servers = [
            {
                "id": "filesystem",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", str(PROJECT_ROOT)],
            },
            {
                "id": "git",
                "command": "npx", 
                "args": ["-y", "@modelcontextprotocol/server-git", f"--repository={PROJECT_ROOT}"],
            },
            {
                "id": "sqlite",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-sqlite", f"{PROJECT_ROOT}/data/stark.db"],
            },
        ]
        
        for server_config in default_servers:
            try:
                await self.client.connect_server(**server_config)
            except Exception as e:
                logger.debug(f"Failed to connect to default MCP server '{server_config['id']}': {e}")
    
    async def execute_with_external_tools(self, 
                                         task: str, 
                                         context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a task using both STARK and external MCP tools.
        
        Args:
            task: Task description
            context: Execution context
            
        Returns:
            Execution result with external tool usage
        """
        if not self._initialized:
            await self.initialize()
            
        start_time = time.time()
        results = {
            "task": task,
            "stark_result": None,
            "external_tools_used": [],
            "combined_output": "",
            "success": False,
        }
        
        try:
            # First, try to solve with STARK
            from core.main import STARK
            stark_result = STARK.process_query(task)
            results["stark_result"] = stark_result
            
            # Analyze if external tools might help
            tools_needed = await self._analyze_external_tool_needs(task, stark_result)
            
            # Use external tools if needed
            for tool_info in tools_needed:
                server_id, tool_name, args = tool_info
                tool_result = await self.client.call_tool(server_id, tool_name, args)
                
                results["external_tools_used"].append({
                    "server_id": server_id,
                    "tool_name": tool_name,
                    "result": tool_result,
                })
            
            # Combine results
            results["combined_output"] = await self._combine_results(
                stark_result, results["external_tools_used"]
            )
            results["success"] = True
            
            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(f"MCP Agent completed task in {elapsed_ms:.2f}ms with {len(tools_needed)} external tools")
            
            return results
            
        except Exception as e:
            logger.error(f"MCP Agent execution failed: {e}", exc_info=True)
            results["error"] = str(e)
            return results
    
    async def _analyze_external_tool_needs(self, 
                                         task: str, 
                                         stark_result: Dict[str, Any]) -> List[tuple]:
        """
        Analyze task to determine if external tools are needed.
        
        Args:
            task: Task description
            stark_result: STARK's initial result
            
        Returns:
            List of (server_id, tool_name, args) tuples
        """
        tools_needed = []
        task_lower = task.lower()
        
        # File system operations
        if any(keyword in task_lower for keyword in ["file", "directory", "list files", "read file"]):
            if "filesystem" in self.client.available_servers:
                tools_needed.append(("filesystem", "read_file", {"path": PROJECT_ROOT}))
        
        # Git operations
        if any(keyword in task_lower for keyword in ["git", "commit", "branch", "repository"]):
            if "git" in self.client.available_servers:
                tools_needed.append(("git", "git_status", {}))
        
        # Database operations
        if any(keyword in task_lower for keyword in ["database", "sql", "query", "table"]):
            if "sqlite" in self.client.available_servers:
                tools_needed.append(("sqlite", "read_query", {"sql": "SELECT name FROM sqlite_master WHERE type='table'"}))
        
        return tools_needed
    
    async def _combine_results(self, 
                              stark_result: Dict[str, Any], 
                              external_results: List[Dict[str, Any]]) -> str:
        """
        Combine STARK result with external tool results.
        
        Args:
            stark_result: Result from STARK
            external_results: Results from external tools
            
        Returns:
            Combined output
        """
        combined = []
        
        # Add STARK response
        if stark_result.get("response"):
            combined.append(f"STARK Analysis:\n{stark_result['response']}")
        
        # Add external tool results
        for result in external_results:
            if result["result"].get("success"):
                tool_output = "\n".join([
                    content.get("text", "") 
                    for content in result["result"].get("content", [])
                    if content.get("type") == "text"
                ])
                combined.append(f"External Tool ({result['server_id']}.{result['tool_name']}):\n{tool_output}")
        
        return "\n\n".join(combined)

# =============================================================================
# MAIN MCP MANAGER
# =============================================================================

class MCPManager:
    """
    Main MCP manager that coordinates server and client functionality.
    """
    
    def __init__(self):
        """Initialize MCP manager."""
        self.server = STARKMCPServer()
        self.client = STARKMCPClient()
        self.agent = MCPAgent()
        self._running = False
    
    async def start(self):
        """Start MCP components."""
        if self._running:
            return
            
        try:
            # Start MCP server in background
            if MCP_SERVER_ENABLED:
                server_task = asyncio.create_task(self.server.start())
                logger.info("MCP server started")
            
            # Initialize MCP agent
            await self.agent.initialize()
            
            self._running = True
            logger.info("MCP Manager started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start MCP Manager: {e}", exc_info=True)
            raise
    
    def stop(self):
        """Stop MCP components."""
        self.server.stop()
        self._running = False
        logger.info("MCP Manager stopped")

# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

_mcp_manager: Optional[MCPManager] = None

def get_mcp_manager() -> MCPManager:
    """Get global MCP manager instance."""
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPManager()
    return _mcp_manager

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    """Test MCP functionality."""
    async def test_mcp():
        manager = get_mcp_manager()
        await manager.start()
        
        # Test server tools
        print("Testing MCP server...")
        
        # Test client connections
        print("Testing MCP client...")
        
        manager.stop()
    
    asyncio.run(test_mcp())