from pathlib import Path
from box import Box
import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"

if not CONFIG_PATH.is_file():
    raise FileNotFoundError(
        f"Configuration file required but not found at {CONFIG_PATH}"
    )

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    raw_config = yaml.safe_load(f) or {}

config: Box = Box(raw_config, frozen_box=True)
