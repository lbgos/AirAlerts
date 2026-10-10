"""Command line entry point: `uv run forecast <command>`."""

import argparse
import asyncio

from . import experiments, scrape, train


def main() -> None:
    parser = argparse.ArgumentParser(prog="forecast")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("login", help="log in to Telegram with a QR code")
    p_scrape = sub.add_parser("scrape", help="download Telegram history into data/raw/")
    p_scrape.add_argument("channels", nargs="*", help="default: all configured channels")
    p_train = sub.add_parser("train", help="fit a config, evaluate on the final test window, write reports/metrics.md")
    p_train.add_argument("--config", default="feat_full", choices=[c.name for c in experiments.CONFIGS])
    p_exp = sub.add_parser("experiments", help="compare model variants on the dev window, write reports/experiments.md")
    p_exp.add_argument("--only", nargs="*", help="run only these config names")
    p_exp.add_argument("--report", default="experiments", help="report name: reports/<name>.md")
    args = parser.parse_args()

    if args.command == "login":
        asyncio.run(scrape.login())
    elif args.command == "scrape":
        asyncio.run(scrape.scrape(args.channels or None))
    elif args.command == "train":
        train.train(experiments.BY_NAME[args.config])
    elif args.command == "experiments":
        experiments.run(args.only, args.report)
