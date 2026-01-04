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
