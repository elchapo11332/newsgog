# Crypto Token Monitor

## Overview

This is a real-time cryptocurrency token monitoring application that tracks new tokens from an external API and automatically posts notifications to a Telegram channel. The system features a web dashboard for monitoring statistics and token history, with live updates via WebSocket connections.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Flask Web Framework**: Main application server handling HTTP requests and WebSocket connections
- **SQLAlchemy ORM**: Database abstraction layer using SQLite as the default database
- **Flask-SocketIO**: Real-time bidirectional communication between server and clients
- **Threading**: Background monitoring service runs in a separate daemon thread

### Data Models
- **PostedToken**: Tracks tokens that have been posted to Telegram (name, contract address, timestamps)
- **MonitorStats**: Stores monitoring statistics (total tokens found/posted, last check time, error states)

### Monitoring Service
- **CryptoMonitor Class**: Core monitoring logic that polls external API every 30 seconds
- **Duplicate Prevention**: Checks database before posting to avoid duplicate notifications
- **Error Handling**: Captures and logs monitoring errors with graceful degradation

### Frontend Architecture
- **Bootstrap 5**: UI framework with dark theme for responsive design
- **Vanilla JavaScript**: Client-side logic for real-time updates and data visualization
- **Socket.IO Client**: Handles real-time communication with the server

### API Structure
- **REST Endpoints**: 
  - `/api/tokens` - Retrieves all posted tokens
  - `/api/stats` - Retrieves monitoring statistics
- **WebSocket Events**:
  - `new_token` - Broadcasts newly discovered tokens
  - `stats_update` - Broadcasts updated statistics
  - `monitor_error` - Broadcasts error notifications

## External Dependencies

### Third-Party APIs
- **Token Discovery API**: `https://steep-thunder-1d39.vapexmeli1.workers.dev/` - Source for new token data
- **Telegram Bot API**: `https://api.telegram.org/bot{token}` - For sending notifications to Telegram channels

### External Services
- **Telegram Integration**: Automated posting of new token discoveries to configured Telegram channel
- **CDN Resources**: Bootstrap CSS/JS, Font Awesome icons, and Socket.IO client library

### Database
- **SQLite**: Default local database (configurable via DATABASE_URL environment variable)
- **Connection Pooling**: Configured with connection recycling and health checks

### Environment Configuration
- `TELEGRAM_TOKEN`: Bot token for Telegram API access
- `CHAT_ID`: Target Telegram channel/chat ID
- `DATABASE_URL`: Database connection string (defaults to SQLite)
- `SESSION_SECRET`: Flask session encryption key