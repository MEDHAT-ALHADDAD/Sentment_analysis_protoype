import subprocess


def main():
    procs = []
    procs.append(
        subprocess.Popen(
            [
                "python",
                "scripts/bronze_ingest.py",
                "--input",
                "data/sample_posts.jsonl",
                "--interval",
                "1",
            ]
        )
    )
    procs.append(subprocess.Popen(["python", "scripts/silver_clean.py"]))
    procs.append(subprocess.Popen(["python", "scripts/silver_features.py"]))
    procs.append(subprocess.Popen(["python", "scripts/serving_sim.py"]))

    for p in procs:
        p.wait()


if __name__ == "__main__":
    main()
