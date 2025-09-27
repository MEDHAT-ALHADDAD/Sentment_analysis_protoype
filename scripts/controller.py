#!/usr/bin/env python3
# scripts/controller.py
import os, sys, time, json, signal, subprocess, threading
from pathlib import Path
from datetime import datetime, timedelta

RAW_TOPIC = Path("topics/social.raw.jsonl")
CLEAN_PROC = ["python", "scripts/silver_clean.py"]
FEAT_PROC = ["python", "scripts/silver_features.py", "--dim", "128"]
SERVE_PROC = ["python", "scripts/serving_sim.py"]

SOURCE_FILE = Path("data/source.jsonl")  # <- put/append your new posts here
OFFSET_FILE = SOURCE_FILE.with_suffix(".offset")
SNAPSHOT_EVERY_MIN = 60  # run gold snapshot every N minutes, aligned
RESTART_MAX = 5


def ensure_dirs():
    for p in [
        RAW_TOPIC.parent,
        Path("silver/cleaned_posts"),
        Path("features/metadata"),
        Path("gold/snapshots"),
        Path("logs"),
        Path("topics"),
        Path("data"),
    ]:
        p.mkdir(parents=True, exist_ok=True)
    # create empty source if missing
    if not SOURCE_FILE.exists():
        SOURCE_FILE.write_text("")


def tail_source_to_raw(stop_evt: threading.Event, poll_sec: float = 1.0):
    """Continuously read new lines from SOURCE_FILE and append to RAW_TOPIC."""
    last = 0
    if OFFSET_FILE.exists():
        try:
            last = int(OFFSET_FILE.read_text())
        except Exception:
            last = 0
    print(f"[producer] starting, offset={last}")
    while not stop_evt.is_set():
        try:
            lines = SOURCE_FILE.read_text(encoding="utf-8").splitlines()
            new = lines[last:]
            if new:
                with open(RAW_TOPIC, "a", encoding="utf-8") as f_out:
                    for line in new:
                        # Validate minimal JSON
                        try:
                            rec = json.loads(line)
                            f_out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        except Exception as e:
                            # write malformed raw to DLQ directly
                            with open(
                                "topics/social.dlq.jsonl", "a", encoding="utf-8"
                            ) as dlq:
                                dlq.write(
                                    json.dumps(
                                        {"error": "producer_bad_json", "raw": line}
                                    )
                                    + "\n"
                                )
                last += len(new)
                OFFSET_FILE.write_text(str(last))
                print(f"[producer] produced {len(new)} new record(s); offset={last}")
        except FileNotFoundError:
            # source may not exist yet
            pass
        time.sleep(poll_sec)
    print("[producer] stopped")


def spawn_supervised(cmd, name, stop_evt: threading.Event):
    """Run a child process with restart/backoff until stop_evt is set."""
    tries, backoff = 0, 1.0
    proc = None
    while not stop_evt.is_set():
        print(f"[{name}] starting: {' '.join(cmd)}")
        proc = subprocess.Popen(cmd)
        rc = None
        # poll until stop or exit
        while not stop_evt.is_set():
            rc = proc.poll()
            if rc is not None:
                break
            time.sleep(0.5)
        if stop_evt.is_set():
            # graceful terminate
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                pass
            print(f"[{name}] terminated by controller")
            return
        # crashed
        print(f"[{name}] exited with code {rc}")
        tries += 1
        if tries > RESTART_MAX:
            print(f"[{name}] reached restart limit ({RESTART_MAX}); giving up")
            return
        print(f"[{name}] restart in {backoff:.1f}s (attempt {tries}/{RESTART_MAX})")
        time.sleep(backoff)
        backoff = min(backoff * 2, 60.0)


def next_aligned_snapshot(now: datetime, every_min: int) -> datetime:
    """Return the next wall-clock time aligned to minute cadence (e.g., :00, :30)."""
    # round up to next multiple of 'every_min' minutes
    minute_block = (now.minute // every_min + 1) * every_min
    delta_min = (minute_block - now.minute) % 60
    dt = now.replace(second=0, microsecond=0) + timedelta(minutes=delta_min)
    # if we rounded to current minute and already past, add interval
    if dt <= now:
        dt += timedelta(minutes=every_min)
    return dt


def snapshot_loop(stop_evt: threading.Event, every_min: int):
    """Periodically trigger gold snapshots on a cadence."""
    while not stop_evt.is_set():
        now = datetime.now()
        target = next_aligned_snapshot(now, every_min)
        wait_s = max(1, int((target - now).total_seconds()))
        print(f"[snapshot] next at {target.isoformat()} (in {wait_s}s)")
        # sleep in small chunks so Ctrl-C is responsive
        slept = 0
        while slept < wait_s and not stop_evt.is_set():
            time.sleep(min(1, wait_s - slept))
            slept += 1
        if stop_evt.is_set():
            break
        # Run snapshot for today's dt (local date)
        date_str = datetime.now().date().isoformat()
        cmd = [sys.executable, "scripts/gold_snapshot.py", "--date", date_str]
        print(f"[snapshot] running: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, check=True)
            print("[snapshot] done")
        except subprocess.CalledProcessError as e:
            print(f"[snapshot] FAILED rc={e.returncode}")


def main():
    ensure_dirs()

    # single stop event shared by threads
    stop_evt = threading.Event()

    # handle Ctrl-C
    def _sigint(_sig, _frm):
        print("\n[controller] SIGINT received, stopping...")
        stop_evt.set()

    signal.signal(signal.SIGINT, _sigint)
    signal.signal(signal.SIGTERM, _sigint)

    # 1) start producer thread (tail source → raw topic)
    prod_thread = threading.Thread(
        target=tail_source_to_raw, args=(stop_evt,), daemon=True
    )
    prod_thread.start()

    # 2) start supervised consumers
    threads = []
    for cmd, name in [
        (CLEAN_PROC, "cleaner"),
        (FEAT_PROC, "features"),
        (SERVE_PROC, "serving"),
    ]:
        t = threading.Thread(
            target=spawn_supervised, args=(cmd, name, stop_evt), daemon=True
        )
        t.start()
        threads.append(t)

    # 3) start snapshot scheduler (Gold)
    snap_thread = threading.Thread(
        target=snapshot_loop, args=(stop_evt, SNAPSHOT_EVERY_MIN), daemon=True
    )
    snap_thread.start()

    # 4) wait until stop
    try:
        while not stop_evt.is_set():
            time.sleep(0.5)
    finally:
        stop_evt.set()
        for t in threads:
            t.join(timeout=5)
        prod_thread.join(timeout=5)
        snap_thread.join(timeout=5)
        print("[controller] stopped")


if __name__ == "__main__":
    main()
