import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.saas.models import Arena

def run():
    print("Migrating arena users...")
    arenas = Arena.objects.all()
    count = 0
    for arena in arenas:
        if arena.user:
            arena.users.add(arena.user)
            count += 1
    print(f"Migrated {count} arenas.")

if __name__ == '__main__':
    run()
