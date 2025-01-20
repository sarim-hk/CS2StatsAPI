from scheduler import create_scheduler

scheduler = create_scheduler()

if __name__ == "__main__":
    scheduler.start()
    
    try:
        while True:
            pass

    except (KeyboardInterrupt, SystemExit):
        print("Shutting down scheduler...")
        scheduler.shutdown()