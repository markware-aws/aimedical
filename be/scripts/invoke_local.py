from __future__ import annotations

import json

from dotenv import load_dotenv


def main() -> None:
    load_dotenv()
    from medical_news.handlers.orchestrator import handler

    summary = handler({}, None)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
