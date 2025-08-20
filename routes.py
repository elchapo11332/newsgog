from flask import render_template, jsonify
from app import app, db, socketio
from models import PostedToken, MonitorStats
from flask_socketio import emit
import logging

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/tokens')
def get_tokens():
    """Get all posted tokens"""
    try:
        tokens = PostedToken.query.order_by(PostedToken.posted_at.desc()).all()
        return jsonify({
            'success': True,
            'tokens': [token.to_dict() for token in tokens]
        })
    except Exception as e:
        logging.error(f"Error fetching tokens: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stats')
def get_stats():
    """Get monitoring statistics"""
    try:
        stats = MonitorStats.query.first()
        if not stats:
            stats = MonitorStats()
            db.session.add(stats)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'stats': stats.to_dict()
        })
    except Exception as e:
        logging.error(f"Error fetching stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logging.info('Client connected to WebSocket')
    emit('connected', {'message': 'Connected to crypto monitor'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logging.info('Client disconnected from WebSocket')
