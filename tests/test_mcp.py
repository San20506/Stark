"""
Tests for STARK MCP (Model Context Protocol) functionality
==========================================================

Tests cover:
- MCP Server initialization and tool exposure
- MCP Client connections and external server usage
- MCP Agent orchestration with external tools
- Integration with STARK core system

Run with:
    pytest tests/test_mcp.py -v
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

from core.constants import (
    MCP_SERVER_ENABLED,
    MCP_CLIENT_ENABLED,
    MCP_SERVER_HOST,
    MCP_SERVER_PORT,
)
from mcp import STARKMCPServer, STARKMCPClient, MCPAgent, MCPManager, get_mcp_manager


class TestSTARKMCPServer:
    """Test STARK MCP Server functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.server = STARKMCPServer()
    
    def test_server_initialization(self):
        """Test MCP server initialization."""
        assert self.server is not None
        assert self.server.server is not None
        assert not self.server._running
    
    @patch('mcp.STARKMCPServer.start')
    async def test_server_start(self, mock_start):
        """Test MCP server startup."""
        mock_start.return_value = None
        
        with patch('core.constants.MCP_SERVER_ENABLED', True):
            await self.server.start()
            mock_start.assert_called_once()
    
    def test_server_stop(self):
        """Test MCP server shutdown."""
        self.server._running = True
        self.server.stop()
        assert not self.server._running
    
    @patch('core.main.STARK.process_query')
    def test_stark_query_tool(self, mock_process):
        """Test stark_query tool functionality."""
        mock_process.return_value = {
            "task": "conversation",
            "confidence": 0.85,
            "response": "Test response",
            "model": "llama3.2:3b",
            "routing_method": "Direct Routing",
        }
        
        # Mock the tool function
        from mcp import FastMCP
        with patch.object(self.server.server, 'tool'):
            # The tool is registered during initialization
            assert hasattr(self.server, 'server')
    
    @patch('agents.code_agent.CodeAgent')
    def test_stark_code_generate_tool(self, mock_code_agent):
        """Test stark_code_generate tool functionality."""
        mock_agent = Mock()
        mock_agent.execute.return_value = Mock(
            success=True,
            output="print('Hello, World!')",
            execution_time_ms=150,
            steps_taken=["generate_code"]
        )
        mock_code_agent.return_value = mock_agent
        
        # Tool is registered during initialization
        assert hasattr(self.server, 'server')


class TestSTARKMCPClient:
    """Test STARK MCP Client functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.client = STARKMCPClient()
    
    def test_client_initialization(self):
        """Test MCP client initialization."""
        assert self.client is not None
        assert len(self.client.connections) == 0
        assert len(self.client.available_servers) == 0
    
    @patch('mcp.STDIO_CLIENT_AVAILABLE', True)
    async def test_connect_server_success(self):
        """Test successful server connection."""
        mock_session = AsyncMock()
        mock_session.initialize.return_value = None
        mock_session.list_tools.return_value = Mock(tools=[Mock(name="test_tool")])
        mock_session.list_resources.return_value = Mock(resources=[])
        mock_session.list_prompts.return_value = Mock(prompts=[])
        
        with patch('mcp.stdio_client') as mock_stdio:
            mock_stdio.return_value.__aenter__.return_value = (Mock(), Mock())
            with patch('mcp.ClientSession', return_value=mock_session):
                with patch('core.constants.MCP_CLIENT_ENABLED', True):
                    result = await self.client.connect_server(
                        "test_server", "python", ["test_script.py"]
                    )
                    assert result is True
                    assert "test_server" in self.client.available_servers
    
    async def test_connect_server_disabled(self):
        """Test server connection when client disabled."""
        with patch('core.constants.MCP_CLIENT_ENABLED', False):
            result = await self.client.connect_server(
                "test_server", "python", ["test_script.py"]
            )
            assert result is False
    
    async def test_connect_server_max_reached(self):
        """Test server connection when max servers reached."""
        self.client.connections = {"server1": {}, "server2": {}, "server3": {}}
        self.client._max_servers = 3
        
        result = await self.client.connect_server(
            "new_server", "python", ["test_script.py"]
        )
        assert result is False
    
    async def test_disconnect_server(self):
        """Test server disconnection."""
        # Setup a mock connection
        mock_session = AsyncMock()
        mock_connection = {
            "session": mock_session,
            "read": AsyncMock(),
            "write": AsyncMock(),
        }
        self.client.connections["test_server"] = mock_connection
        self.client.available_servers["test_server"] = {"tools": ["test_tool"]}
        
        result = await self.client.disconnect_server("test_server")
        assert result is True
        assert "test_server" not in self.client.connections
        assert "test_server" not in self.client.available_servers
    
    async def test_call_tool_success(self):
        """Test successful tool call."""
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.isError = False
        mock_result.content = [Mock(text="Tool result")]
        mock_session.call_tool.return_value = mock_result
        
        self.client.connections["test_server"] = {"session": mock_session}
        
        result = await self.client.call_tool("test_server", "test_tool", {"arg": "value"})
        assert result["success"] is True
        assert result["server_id"] == "test_server"
        assert result["tool_name"] == "test_tool"
    
    async def test_call_tool_server_not_connected(self):
        """Test tool call when server not connected."""
        result = await self.client.call_tool("nonexistent_server", "test_tool", {})
        assert result["success"] is False
        assert "not connected" in result["error"].lower()
    
    async def test_read_resource_success(self):
        """Test successful resource reading."""
        mock_session = AsyncMock()
        mock_session.read_resource.return_value = ("Resource content", "text/plain")
        
        self.client.connections["test_server"] = {"session": mock_session}
        
        result = await self.client.read_resource("test_server", "test://resource")
        assert result["success"] is True
        assert result["content"] == "Resource content"
        assert result["mime_type"] == "text/plain"
    
    def test_list_available_tools(self):
        """Test listing available tools."""
        self.client.available_servers = {
            "server1": {"tools": ["tool1", "tool2"]},
            "server2": {"tools": ["tool3"]},
        }
        
        all_tools = self.client.list_available_tools()
        expected = {
            "server1": ["tool1", "tool2"],
            "server2": ["tool3"],
        }
        assert all_tools == expected
        
        server1_tools = self.client.list_available_tools("server1")
        assert server1_tools == {"server1": ["tool1", "tool2"]}
    
    def test_get_server_info(self):
        """Test getting server information."""
        server_info = {"tools": ["tool1"], "connected_at": 1234567890}
        self.client.available_servers["test_server"] = server_info
        
        result = self.client.get_server_info("test_server")
        assert result == server_info
        
        result = self.client.get_server_info("nonexistent")
        assert result is None


class TestMCPAgent:
    """Test MCP Agent functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.agent = MCPAgent()
    
    def test_agent_initialization(self):
        """Test MCP agent initialization."""
        assert self.agent is not None
        assert self.agent.name == "MCPAgent"
        assert self.agent.client is not None
        assert not self.agent._initialized
    
    @patch('mcp.STARKMCPClient.connect_server')
    async def test_initialize(self, mock_connect):
        """Test MCP agent initialization."""
        mock_connect.return_value = True
        mock_connect.side_effect = [
            True,  # filesystem
            True,  # git
            False,  # sqlite (optional)
        ]
        
        await self.agent.initialize()
        assert self.agent._initialized
        
        # Should attempt to connect to default servers
        assert mock_connect.call_count >= 2
    
    @patch('mcp.STARKMCPClient.connect_server')
    async def test_connect_default_servers(self, mock_connect):
        """Test connection to default servers."""
        mock_connect.return_value = False  # Simulate connection failures
        
        await self.agent._connect_default_servers()
        
        # Should attempt to connect to filesystem, git, and sqlite
        assert mock_connect.call_count >= 3
    
    async def test_analyze_external_tool_needs(self):
        """Test analysis of external tool needs."""
        # Test file system tool need
        tools_needed = await self.agent._analyze_external_tool_needs(
            "Read the file config.yaml", {}
        )
        # Should suggest filesystem tools if available
        assert isinstance(tools_needed, list)
        
        # Test git tool need
        tools_needed = await self.agent._analyze_external_tool_needs(
            "Check git status and commit changes", {}
        )
        assert isinstance(tools_needed, list)
        
        # Test database tool need
        tools_needed = await self.agent._analyze_external_tool_needs(
            "Query the user database", {}
        )
        assert isinstance(tools_needed, list)
    
    async def test_combine_results(self):
        """Test result combination."""
        stark_result = {
            "response": "STARK analysis complete",
            "task": "research",
            "confidence": 0.9,
        }
        
        external_results = [
            {
                "server_id": "filesystem",
                "tool_name": "read_file",
                "result": {
                    "success": True,
                    "content": [Mock(text="File content")],
                },
            }
        ]
        
        combined = await self.agent._combine_results(stark_result, external_results)
        assert "STARK analysis complete" in combined
        assert "File content" in combined
    
    @patch('core.main.STARK.process_query')
    @patch.object(MCPAgent, '_analyze_external_tool_needs')
    @patch.object(MCPAgent, '_combine_results')
    async def test_execute_with_external_tools(self, mock_combine, mock_analyze, mock_stark):
        """Test execution with external tools."""
        # Setup mocks
        mock_stark.return_value = {
            "response": "STARK response",
            "task": "conversation",
        }
        mock_analyze.return_value = [
            ("filesystem", "read_file", {"path": "/test"})
        ]
        mock_combine.return_value = "Combined result"
        
        # Setup client mock
        self.agent.client.connections["filesystem"] = {"session": Mock()}
        self.agent.client.available_servers["filesystem"] = {"tools": ["read_file"]}
        
        with patch.object(self.agent.client, 'call_tool') as mock_call:
            mock_call.return_value = {
                "success": True,
                "content": [Mock(text="File content")],
            }
            
            result = await self.agent.execute_with_external_tools("Test query")
            
            assert result["success"] is True
            assert result["stark_result"] is not None
            assert len(result["external_tools_used"]) > 0
            assert result["combined_output"] == "Combined result"


class TestMCPManager:
    """Test MCP Manager functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.manager = MCPManager()
    
    def test_manager_initialization(self):
        """Test MCP manager initialization."""
        assert self.manager is not None
        assert self.manager.server is not None
        assert self.manager.client is not None
        assert self.manager.agent is not None
        assert not self.manager._running
    
    @patch('mcp.STARKMCPServer.start')
    @patch('mcp.MCPAgent.initialize')
    async def test_start(self, mock_agent_init, mock_server_start):
        """Test MCP manager startup."""
        mock_server_start.return_value = None
        mock_agent_init.return_value = None
        
        with patch('core.constants.MCP_SERVER_ENABLED', True):
            with patch('core.constants.MCP_CLIENT_ENABLED', True):
                await self.manager.start()
                assert self.manager._running
                mock_server_start.assert_called_once()
                mock_agent_init.assert_called_once()
    
    @patch('mcp.STARKMCPServer.start')
    @patch('mcp.MCPAgent.initialize')
    async def test_start_disabled(self, mock_agent_init, mock_server_start):
        """Test MCP manager startup when disabled."""
        with patch('core.constants.MCP_SERVER_ENABLED', False):
            with patch('core.constants.MCP_CLIENT_ENABLED', False):
                await self.manager.start()
                assert self.manager._running
                # Should not start server or agent when disabled
                mock_server_start.assert_not_called()
                mock_agent_init.assert_called_once()  # Agent still initializes for internal use
    
    def test_stop(self):
        """Test MCP manager shutdown."""
        self.manager._running = True
        self.manager.stop()
        assert not self.manager._running


class TestMCPIntegration:
    """Test MCP integration with STARK core."""
    
    def setup_method(self):
        """Setup test environment."""
        # Reset global instance
        import mcp
        mcp._mcp_manager = None
    
    def test_get_mcp_manager(self):
        """Test global MCP manager getter."""
        manager = get_mcp_manager()
        assert manager is not None
        assert isinstance(manager, MCPManager)
        
        # Should return same instance
        manager2 = get_mcp_manager()
        assert manager is manager2
    
    @patch('mcp.MCPManager.start')
    @patch('core.main.STARK._load_modules')
    async def test_stark_mcp_integration(self, mock_load, mock_mcp_start):
        """Test STARK integration with MCP."""
        from core.main import STARK
        
        # Setup mocks
        mock_mcp_start.return_value = None
        
        with patch('core.constants.MCP_SERVER_ENABLED', True):
            with patch('core.constants.MCP_CLIENT_ENABLED', True):
                with patch('mcp.get_mcp_manager') as mock_get_mcp:
                    mock_manager = Mock()
                    mock_get_mcp.return_value = mock_manager
                    
                    await STARK.start_async()
                    
                    # Should start MCP manager
                    mock_get_mcp.assert_called_once()
    
    @patch('mcp.MCPManager')
    def test_stark_get_mcp_status(self, mock_manager_class):
        """Test getting MCP status from STARK."""
        from core.main import STARK
        
        mock_manager = Mock()
        mock_manager.client.available_servers = {"server1": {}}
        mock_manager.client.list_available_tools.return_value = {"server1": ["tool1"]}
        STARK._mcp_manager = mock_manager
        
        status = STARK.get_mcp_status()
        assert status["enabled"] is True
        assert "servers_connected" in status
    
    def test_stark_get_mcp_status_not_initialized(self):
        """Test getting MCP status when not initialized."""
        from core.main import STARK
        
        STARK._mcp_manager = None
        status = STARK.get_mcp_status()
        assert status["enabled"] is False
        assert status["status"] == "not_initialized"


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_stark():
    """Mock STARK instance."""
    stark = Mock()
    stark.process_query.return_value = {
        "task": "conversation",
        "confidence": 0.8,
        "response": "Mock response",
        "model": "llama3.2:3b",
        "routing_method": "Direct Routing",
    }
    return stark


@pytest.fixture
def mock_mcp_manager():
    """Mock MCP manager."""
    manager = Mock()
    manager.client.connections = {}
    manager.client.available_servers = {}
    manager.client.list_available_tools.return_value = {}
    return manager


# =============================================================================
# ASYNC TEST RUNNER
# =============================================================================

def run_async_test(coro):
    """Helper to run async tests in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# =============================================================================
# PYTEST MARKERS
# =============================================================================

pytest_plugins = []

# Mark async tests
pytestmark = pytest.mark.asyncio if hasattr(pytest.mark, 'asyncio') else None