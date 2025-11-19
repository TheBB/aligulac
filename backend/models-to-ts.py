from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic.json_schema import models_json_schema

from aligulac import models


def is_model(obj: Any) -> bool:
    return (
        inspect.isclass(obj)
        and issubclass(obj, BaseModel)
        and not obj.__name__.startswith("_")
        and obj is not BaseModel
    )


def main() -> None:
    classes = list({
        obj for obj in models.__dict__.values()
        if is_model(obj)
    })

    names: dict[str, Any] = {}
    for cls in classes:
        if cls.__name__ in names:
            print(f"Duplicated name: {names[cls.__name__]} and {cls}")
            sys.exit(1)
        names[cls.__name__] = cls

    _, schema = models_json_schema([(cls, "serialization") for cls in classes], by_alias=False)
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"

    schema_file = Path(__file__).parent / "schema.json"
    with schema_file.open("w") as f:
        json.dump(schema, f, indent=2)


if __name__ == "__main__":
    main()
