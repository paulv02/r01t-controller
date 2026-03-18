import time
import json
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def check_file():
    FILE_DIR = os.getenv("LOG_DIR")
    os.makedirs(FILE_DIR, exist_ok=True)
    return FILE_DIR

FILE_PATH = check_file()

def log(level, logger, msg):
    try:
        time_now = int(time.time())
        level_upper = str(level).upper()
        logger_lower = str(logger).lower()
        message = str(msg).replace('\n', '')
        log_line = { 'time': time_now,
                    'level': level_upper,
                    'logger': logger_lower,
                    'message': message }
        with open(f'{FILE_PATH}/{datetime.now().strftime('%y-%m-%d')}.log', 'a') as f:
            f.write(json.dumps(log_line) + '\n')
    except Exception as e:
        print(e)