import pytest

from bot.config import ConfigurationError, load_settings

REQUIRED_ENVIRONMENT = {
    "BOT_TOKEN": "token",
    "SUPPORT_GROUP_ID": "-100123",
    "DATABASE_URL": "postgresql://localhost/supportx",
}


def test_settings_are_loaded_with_defaults():
    settings = load_settings(REQUIRED_ENVIRONMENT)

    assert settings.support_group_id == -100123
    assert settings.auto_close_after_days == 7
    assert settings.internal_note_prefix == "//"
    assert settings.customer_messages_per_minute == 30
    assert settings.new_tickets_per_minute == 20


@pytest.mark.parametrize("missing_name", sorted(REQUIRED_ENVIRONMENT))
def test_missing_required_variable_is_reported(missing_name):
    environment = {name: value for name, value in REQUIRED_ENVIRONMENT.items() if name != missing_name}

    with pytest.raises(ConfigurationError, match=missing_name):
        load_settings(environment)


def test_non_numeric_group_id_is_reported():
    with pytest.raises(ConfigurationError, match="SUPPORT_GROUP_ID"):
        load_settings(REQUIRED_ENVIRONMENT | {"SUPPORT_GROUP_ID": "support"})


def test_every_text_can_be_overridden():
    settings = load_settings(REQUIRED_ENVIRONMENT | {"MSG_WELCOME": "Привет!", "MSG_OPEN_CHAT_BUTTON": "Чат"})

    assert settings.texts.welcome == "Привет!"
    assert settings.texts.open_chat_button == "Чат"


def test_unknown_placeholder_in_text_is_reported():
    with pytest.raises(ConfigurationError, match="MSG_TOPIC_TITLE"):
        load_settings(REQUIRED_ENVIRONMENT | {"MSG_TOPIC_TITLE": "Ticket of {customer}"})
