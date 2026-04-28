from __future__ import annotations

import argparse
import time

from sqlalchemy import text

from backend.app.db.session import SessionLocal


def main() -> None:
    parser = argparse.ArgumentParser(description="Watch 84000 Tibetan Discourses import progress.")
    parser.add_argument("--interval", type=int, default=30, help="Polling interval in seconds.")
    parser.add_argument("--iterations", type=int, default=0, help="Number of polls before exiting. 0 means run forever.")
    args = parser.parse_args()

    iteration = 0
    while True:
        with SessionLocal() as session:
            row = session.execute(
                text(
                    """
                    select
                      (select count(*) from text_versions where source_id = 'source-tibetan-84000-discourses') as text_versions,
                      (select count(*) from segments s join text_versions tv on tv.id = s.text_version_id where tv.source_id = 'source-tibetan-84000-discourses') as segments,
                      (select count(*) from segments s join text_versions tv on tv.id = s.text_version_id
                        where tv.source_id = 'source-tibetan-84000-discourses'
                          and s.content_gloss is not null
                          and s.content_gloss <> '') as gloss_segments
                    """
                )
            ).first()
        print(
            f"watchdog: text_versions={row.text_versions}, segments={row.segments}, gloss_segments={row.gloss_segments}",
            flush=True,
        )
        iteration += 1
        if args.iterations and iteration >= args.iterations:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
