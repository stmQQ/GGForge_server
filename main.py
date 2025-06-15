# main.py
import os
from dotenv import load_dotenv
from app import create_app

load_dotenv()
app = create_app()  # Создаём объект app

if __name__ == '__main__':
    from app.apscheduler_tasks import register_scheduler
    with app.app_context():
        register_scheduler(app)
        port = int(os.getenv("PORT", 5000))
        app.run(host="0.0.0.0", port=port)
