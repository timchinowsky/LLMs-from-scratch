from dataclasses import dataclass
from pathlib import Path
import tomllib
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass(frozen=True)
class Settings:
    data_dir: Path = Path("state")
    origin: str = "http://127.0.0.1:8765"
    timezone: str = "America/Los_Angeles"
    synthetic: bool = True
    min_free_mb: int = 100

    def __post_init__(self):
        if self.origin != "http://127.0.0.1:8765":
            raise ValueError("This development release only supports http://127.0.0.1:8765")
        if not self.synthetic:
            raise ValueError("Real audio is not implemented; synthetic must remain true")
        if not isinstance(self.min_free_mb, int) or self.min_free_mb < 1:
            raise ValueError("min_free_mb must be a positive integer")
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("timezone must be a valid IANA timezone") from None

    @classmethod
    def load(cls, path: str | None):
        if not path:
            return cls()
        with open(path, "rb") as file:
            data = tomllib.load(file)
        allowed = {"data_dir", "origin", "timezone", "synthetic", "min_free_mb"}
        if data.keys() - allowed:
            raise ValueError("Unknown configuration setting; see config.example.toml")
        if "data_dir" in data:
            data["data_dir"] = Path(data["data_dir"])
        return cls(**data)
