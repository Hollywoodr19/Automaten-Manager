#!/usr/bin/env python
"""
Automaten Manager v2.0 - Startdatei
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app import create_app, db
from app.models import User, Device, Entry, Expense

# Determine environment
env = os.getenv('FLASK_ENV', 'development')
app = create_app(env)

# Shell context for debugging
@app.shell_context_processor
def make_shell_context():
    """Context for flask shell"""
    return {
        'db': db,
        'User': User,
        'Device': Device,
        'Entry': Entry,
        'Expense': Expense,
    }

if __name__ == '__main__':
    # Development server
    if env == 'development':
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True,
            use_reloader=True
        )
    else:
        # Production: Use Gunicorn
        print("Please use Gunicorn in production: gunicorn -c gunicorn_config.py run:app")
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=False
        )