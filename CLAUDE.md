# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

CDS Videos is a video repository platform built on top of the Invenio framework. It provides a complete video management system with upload, transcoding, metadata management, and publishing capabilities for CERN's video content.

## Prerequisites

- Python 3.9
- Node.js v18
- FFmpeg v5.0
- Docker v2 or later

## Development Commands

### Setup
```bash
# Initial setup (run once)
docker compose up -d
./scripts/bootstrap
./scripts/setup

# Test setup
./scripts/setup-tests
```

### Development Workflow
```bash
# Start web server
./scripts/server

# Start Celery workers (separate terminal)
./scripts/celery

# Watch frontend assets (separate terminal)
./scripts/assets-watch

# Build assets manually
invenio collect -v
invenio webpack buildall
```

### Testing
```bash
# Run all tests
./run-tests.sh

# Run specific test file
./run-tests.sh tests/unit/test_example.py

# Run specific test function
./run-tests.sh tests/unit/test_example.py -k "test_specific_function"

# Keep services running during tests
./run-tests.sh -K
```

## Architecture Overview

### Core Components

**Video Processing Pipeline (`cds/modules/flows/`)**
- Handles video upload, transcoding, and metadata extraction
- Uses Celery for asynchronous processing
- Integrates with FFmpeg for video operations

**Deposit System (`cds/modules/deposit/`)**
- Manages video and project creation workflow
- Provides REST API endpoints for content submission
- Includes validation and permission systems

**Records Management (`cds/modules/records/`)**
- Handles published video records and metadata
- Provides search and retrieval functionality
- Manages serialization for various formats (JSON, DataCite, SMIL)

**Theme and UI (`cds/modules/theme/`)**
- Angular-based frontend with Bootstrap 3
- Video player integration and responsive design
- Asset management through Webpack

### Key Modules

- **`cds/modules/previewer/`**: Video preview and embedding functionality
- **`cds/modules/stats/`**: Analytics and usage statistics
- **`cds/modules/opencast/`**: Integration with Opencast video platform
- **`cds/modules/ffmpeg/`**: Video processing utilities
- **`cds/modules/legacy/`**: Backward compatibility and redirects

### Configuration

Main configuration is in `cds/config.py`, which includes:
- Database and search engine settings
- Celery task configuration
- Video processing parameters
- Authentication and permissions

### Frontend Architecture

The frontend uses:
- AngularJS 1.5.x with Angular Schema Form
- CKEditor for rich text editing
- Invenio-specific JavaScript modules
- SCSS with Bootstrap 3 for styling

Assets are defined in `cds/modules/theme/webpack.py` and bundled using Webpack.

### Video Workflow

1. **Project Creation**: Users create projects to organize videos
2. **Video Upload**: Files are uploaded to buckets with metadata
3. **Flow Processing**: Background tasks handle transcoding and frame extraction
4. **Publishing**: Completed videos are made publicly available
5. **Access Control**: Permissions managed through CERN authentication

### REST API

The platform provides REST endpoints for:
- `/api/deposits/project/` - Project management
- `/api/deposits/video/` - Video management  
- `/api/flows/` - Processing workflow management
- `/api/files/` - File upload and management

### Database Models

Key models include:
- Video and Project deposits with metadata
- Flow processing states and tasks
- User permissions and access controls
- Statistics and analytics data

### Testing Structure

- `tests/unit/` - Unit tests for individual components
- `tests/functional/` - Robot Framework integration tests
- Test data and fixtures in `tests/data/`

The application uses Docker services for testing dependencies (PostgreSQL, Redis, RabbitMQ, OpenSearch).