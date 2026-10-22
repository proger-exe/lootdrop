"""Tests for fulfillment schema validation."""

from app.domain.catalog.fulfillment import validate_fulfillment_data, validate_fulfillment_schema


def test_valid_schema_accepts_choice() -> None:
    """A choice field with options is valid."""

    schema = {
        "fields": [
            {
                "key": "server",
                "label": "Сервер",
                "type": "choice",
                "required": True,
                "options": ["Survival", "Classic"],
            },
        ],
    }
    validate_fulfillment_schema(schema)
    assert validate_fulfillment_data(schema, {"server": "Survival"}) == []


def test_invalid_choice_value_returns_field_error() -> None:
    """A choice outside configured options is rejected."""

    schema = {
        "fields": [
            {
                "key": "server",
                "label": "Сервер",
                "type": "choice",
                "required": True,
                "options": ["Survival"],
            },
        ],
    }
    errors = validate_fulfillment_data(schema, {"server": "Classic"})
    assert errors[0].key == "server"
