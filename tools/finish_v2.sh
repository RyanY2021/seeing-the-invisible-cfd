#!/usr/bin/env bash
# v2 finish: wait for every shot to be fully rendered -> SFX/mix -> subtitles -> full 1080p compose
# -> copy to the delivery folder in $V2_DELIVER_DIR (if set).
cd "/d/Creative/CFD Intro"
LOG=cache/v2/finish.log
echo "[$(date +%H:%M:%S)] waiting for renders" >> $LOG
until .venv/Scripts/python.exe tools/check_renders_v2.py | tail -1 | grep -q "(100%)" && ! tasklist 2>/dev/null | grep -qi "blender.exe"; do sleep 60; done
echo "[$(date +%H:%M:%S)] renders complete" >> $LOG
cd src
../.venv/Scripts/python.exe sfx_v2.py >> ../$LOG 2>&1
../.venv/Scripts/python.exe make_srt_v2.py >> ../$LOG 2>&1
../.venv/Scripts/python.exe compose_v2.py --jobs 7 >> ../$LOG 2>&1 || { echo "COMPOSE FAILED" >> ../$LOG; exit 1; }
cd ..
OUT=output/Seeing_the_Invisible_CFD_v2.mp4
[ -s "$OUT" ] || { echo "NO OUTPUT" >> $LOG; exit 1; }
DEST="${V2_DELIVER_DIR:-}"
[ -n "$DEST" ] && cp "$OUT" "$DEST/" && echo "[$(date +%H:%M:%S)] COPIED: $(ls -la "$DEST/Seeing_the_Invisible_CFD_v2.mp4")" >> $LOG
echo "FINISHED" >> $LOG
