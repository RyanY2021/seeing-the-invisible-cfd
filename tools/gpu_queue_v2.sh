#!/usr/bin/env bash
# Sequential GPU job runner. Jobs: one shell command per line in cache/gpu_queue.txt.
# Finished line numbers go to cache/gpu_queue.done. A line "STOP" ends the runner.
# Safe to restart: already-finished lines are skipped (Blender renders also skip existing frames).
cd "/d/Creative/CFD Intro"
Q=cache/v2/queue.txt; D=cache/v2/queue.done; touch "$Q" "$D"
while true; do
  n=0; ran=0
  while IFS= read -r line || [ -n "$line" ]; do
    n=$((n+1))
    [ -z "$line" ] && continue
    case "$line" in \#*) continue;; esac
    grep -qx "$n" "$D" && continue
    [ "$line" = "STOP" ] && exit 0
    echo "[$(date +%H:%M:%S)] START $n: $line" >> cache/v2/queue.log
    bash -c "$line" >> cache/v2/queue_jobs.log 2>&1
    echo "[$(date +%H:%M:%S)] END $n (exit $?)" >> cache/v2/queue.log
    echo "$n" >> "$D"; ran=1; break
  done < "$Q"
  [ $ran -eq 0 ] && sleep 20
done
