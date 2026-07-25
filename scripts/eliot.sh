#!/bin/bash
# ELIOT service manager for Jetson Orin Nano

ELIOT_DIR="/home/jetson/El1ot"
SESSION="eliot"
LOG_FILE="/tmp/eliot.log"

case "$1" in
  start)
    if tmux has-session -t "$SESSION" 2>/dev/null; then
      echo "ELIOT is already running (tmux session: $SESSION)"
      exit 1
    fi
    echo "Starting ELIOT..."
    tmux new-session -d -s "$SESSION" \
      "cd $ELIOT_DIR && python3 -m uvicorn core.main:app --host 0.0.0.0 --port 8000 2>&1 | tee $LOG_FILE"
    sleep 5
    if curl -s -L http://localhost:8000/health > /dev/null 2>&1; then
      echo "ELIOT started successfully"
    else
      echo "ELIOT starting... check: tmux attach -t $SESSION"
    fi
    ;;
  stop)
    if tmux has-session -t "$SESSION" 2>/dev/null; then
      echo "Stopping ELIOT..."
      tmux kill-session -t "$SESSION"
      echo "ELIOT stopped"
    else
      echo "ELIOT is not running"
    fi
    ;;
  restart)
    $0 stop
    sleep 1
    $0 start
    ;;
  status)
    if tmux has-session -t "$SESSION" 2>/dev/null; then
      echo "ELIOT is running (tmux session: $SESSION)"
      curl -s -L http://localhost:8000/health | python3 -m json.tool 2>/dev/null
    else
      echo "ELIOT is not running"
    fi
    ;;
  logs)
    tmux attach -t "$SESSION"
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status|logs}"
    exit 1
    ;;
esac
