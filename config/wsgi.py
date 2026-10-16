"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os
import shutil
from pathlib import Path

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Garante inicialização automática do banco no Render a partir do snapshot seed
base_dir = Path(__file__).resolve().parent.parent
active_db = base_dir / 'db.sqlite3'
seed_db = base_dir / 'db_seed_clean.sqlite3'

try:
    if not active_db.exists() or active_db.stat().st_size == 0:
        if seed_db.exists():
            shutil.copyfile(seed_db, active_db)
            print("[INFO] Banco db.sqlite3 inicializado com sucesso a partir de db_seed_clean.sqlite3")
except Exception as e:
    print(f"[WARN] Falha ao verificar/copiar banco seed inicial: {e}")

application = get_wsgi_application()
