"""Fulfillment schema validation."""

from dataclasses import dataclass
from typing import Any

from app.data.enums import FulfillmentFieldType


@dataclass(frozen=True, slots=True)
class FieldError:
    """Validation error for one fulfillment field."""

    key: str
    message: str


class FulfillmentSchemaError(ValueError):
    """Raised when a product fulfillment schema is invalid."""


def validate_fulfillment_schema(schema: dict[str, Any]) -> None:
    """Validate a product fulfillment schema."""

    fields = schema.get("fields")
    if not isinstance(fields, list):
        raise FulfillmentSchemaError("fulfillment_schema.fields must be a list")
    keys: set[str] = set()
    for field in fields:
        if not isinstance(field, dict):
            raise FulfillmentSchemaError("fulfillment field must be an object")
        key = field.get("key")
        if not isinstance(key, str) or not key:
            raise FulfillmentSchemaError("fulfillment field key is required")
        if key in keys:
            raise FulfillmentSchemaError(f"duplicate fulfillment field key: {key}")
        keys.add(key)
        label = field.get("label")
        if not isinstance(label, str) or not label:
            raise FulfillmentSchemaError(f"label is required for field {key}")
        raw_type = field.get("type")
        if not isinstance(raw_type, str):
            raise FulfillmentSchemaError(f"type is required for field {key}")
        try:
            field_type = FulfillmentFieldType(raw_type)
        except ValueError as error:
            raise FulfillmentSchemaError(f"unsupported field type for {key}") from error
        if field_type == FulfillmentFieldType.CHOICE:
            options = field.get("options")
            if not isinstance(options, list) or not all(
                isinstance(option, str) for option in options
            ):
                raise FulfillmentSchemaError(f"choice options are required for {key}")


def validate_fulfillment_data(schema: dict[str, Any], data: dict[str, Any]) -> list[FieldError]:
    """Validate checkout data against product fulfillment schema."""

    validate_fulfillment_schema(schema)
    errors: list[FieldError] = []
    for field in schema["fields"]:
        key = field["key"]
        value = data.get(key)
        required = bool(field.get("required", False))
        if required and (value is None or value == ""):
            errors.append(FieldError(key, "Обязательное поле"))
            continue
        if value is None or value == "":
            continue
        field_type = FulfillmentFieldType(field["type"])
        if field_type == FulfillmentFieldType.INTEGER and not str(value).isdigit():
            errors.append(FieldError(key, "Введите число"))
        if field_type == FulfillmentFieldType.CHOICE and value not in field["options"]:
            errors.append(FieldError(key, "Выберите значение из списка"))
        if field_type == FulfillmentFieldType.TELEGRAM_USERNAME and not str(value).startswith("@"):
            errors.append(FieldError(key, "Username должен начинаться с @"))
        if field_type == FulfillmentFieldType.URL and not str(value).startswith(
            ("http://", "https://")
        ):
            errors.append(FieldError(key, "Введите ссылку"))
        min_length = field.get("min_length")
        max_length = field.get("max_length")
        if isinstance(value, str) and isinstance(min_length, int) and len(value) < min_length:
            errors.append(FieldError(key, f"Минимум символов: {min_length}"))
        if isinstance(value, str) and isinstance(max_length, int) and len(value) > max_length:
            errors.append(FieldError(key, f"Максимум символов: {max_length}"))
    return errors
