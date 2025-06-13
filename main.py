from app import create_app


app = create_app()  # 'prod' для продакшена

if __name__ == '__main__':
    print(app)
    from app.apscheduler_tasks import register_scheduler
    with app.app_context():
        register_scheduler(app)
        app.run()
