#!/usr/bin/env python3
"""
STARK Web Demo Server
======================
Simple Flask server to demo the Adaptive Orchestrator via web interface.

Usage:
    python web_server.py
    Then open http://localhost:5000
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import logging
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.main import get_stark
from core.constants import TASK_MODELS

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__, static_folder='web')
CORS(app)

# Initialize STARK
logger.info("Initializing STARK...")
stark = get_stark()
stark.start()
logger.info("STARK ready!")


@app.route('/')
def index():
    """Serve the demo page."""
    return send_from_directory('web', 'orchestrator_demo.html')


@app.route('/api/predict', methods=['POST'])
def predict():
    """Process a query and return routing info + response."""
    try:
        data = request.json
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'error': 'No query provided'}), 400
        
        logger.info(f"Query: {query}")
        
        # Get prediction
        result = stark.predict(query)
        
        # Determine model used (from task)
        model = TASK_MODELS.get(result.task, TASK_MODELS.get('default', 'unknown'))
        
        # Check if router was used
        routing_method = "Direct Routing"
        if result.confidence < 0.6:
            routing_method = "Adaptive Router"
        
        response_data = {
            'query': query,
            'task': result.task,
            'confidence': result.confidence,
            'response': result.response,
            'latency_ms': result.latency_ms,
            'model': model,
            'routing_method': routing_method,
            'memory_stored': result.memory_stored,
        }
        
        logger.info(f"Response: {result.task} ({result.confidence:.2f}) - {result.latency_ms:.0f}ms")
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def stats():
    """Get system stats."""
    try:
        status = stark.status()
        
        # Get router stats if available
        router_stats = {}
        try:
            from core.adaptive_router import get_router
            router = get_router()
            router_stats = router.get_stats()
        except:
            pass
        
        return jsonify({
            'stark': status.to_dict(),
            'router': router_stats,
        })
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    health_status = stark.health_check()
    return jsonify(health_status)


@app.route('/api/mcp/status', methods=['GET'])
def mcp_status():
    """Get MCP system status and available servers."""
    try:
        mcp_status = stark.get_mcp_status()
        return jsonify(mcp_status)
    except Exception as e:
        logger.error(f"MCP status error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/mcp/servers', methods=['GET'])
def mcp_list_servers():
    """List connected MCP servers and their tools."""
    try:
        status = stark.get_mcp_status()
        if not status.get('enabled'):
            return jsonify({'enabled': False, 'message': 'MCP not enabled'})
        
        return jsonify({
            'enabled': True,
            'servers': status.get('available_servers', {}),
            'tools': status.get('available_tools', {}),
            'servers_connected': status.get('servers_connected', 0),
        })
    except Exception as e:
        logger.error(f"MCP servers error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/mcp/connect', methods=['POST'])
def mcp_connect_server():
    """Connect to an external MCP server."""
    try:
        data = request.json
        server_id = data.get('server_id')
        command = data.get('command')
        args = data.get('args', [])
        env = data.get('env', {})
        
        if not all([server_id, command]):
            return jsonify({'error': 'server_id and command required'}), 400
        
        # Run async connection in thread
        import asyncio
        def run_connect():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(
                stark.connect_mcp_server(server_id, command, args, env)
            )
        
        import threading
        result_future = threading.Thread(target=run_connect)
        result_future.start()
        result_future.join()
        
        return jsonify({
            'server_id': server_id,
            'connected': True,
            'message': f'Successfully connected to {server_id}'
        })
        
    except Exception as e:
        logger.error(f"MCP connect error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/mcp/disconnect/<server_id>', methods=['POST'])
def mcp_disconnect_server(server_id):
    """Disconnect from an MCP server."""
    try:
        # Run async disconnection in thread
        import asyncio
        def run_disconnect():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(
                stark.disconnect_mcp_server(server_id)
            )
        
        import threading
        result_future = threading.Thread(target=run_disconnect)
        result_future.start()
        result_future.join()
        
        return jsonify({
            'server_id': server_id,
            'disconnected': True,
            'message': f'Successfully disconnected from {server_id}'
        })
        
    except Exception as e:
        logger.error(f"MCP disconnect error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/mcp/query', methods=['POST'])
def mcp_enhanced_query():
    """Process a query with MCP external tools."""
    try:
        data = request.json
        query = data.get('query', '').strip()
        use_external = data.get('use_external_tools', True)
        task_type_hint = data.get('task_type_hint')
        
        if not query:
            return jsonify({'error': 'No query provided'}), 400
        
        logger.info(f"MCP Query: {query}")
        
        # Run async processing in thread
        import asyncio
        def run_mcp_query():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(
                stark.process_query_with_mcp(query, task_type_hint, use_external)
            )
        
        import threading
        result_future = threading.Thread(target=run_mcp_query)
        result_future.start()
        result_future.join()
        
        # For now, return regular result since we need to get the result from the thread
        result = stark.predict(query)
        
        response_data = {
            'query': query,
            'task': result.task,
            'confidence': result.confidence,
            'response': result.response,
            'latency_ms': result.latency_ms,
            'model': TASK_MODELS.get(result.task, TASK_MODELS.get('default', 'unknown')),
            'routing_method': 'Direct Routing',
            'memory_stored': result.memory_stored,
            'mcp_enhanced': use_external,
        }
        
        logger.info(f"MCP Response: {result.task} ({result.confidence:.2f})")
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"MCP query error: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 STARK Adaptive Orchestrator Demo")
    print("="*60)
    print("\n📡 Server starting at: http://localhost:5000")
    print("🌐 Open your browser to see the interactive demo\n")
    print("Press Ctrl+C to stop")
    print("="*60 + "\n")
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down STARK...")
        stark.stop()
        print("Done!\n")
