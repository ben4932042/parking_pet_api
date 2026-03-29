run-server:
    nohup poetry run python main.py > output.log 2>&1 &
stop-server:
     kill -9 $(lsof -t -i:8000)
