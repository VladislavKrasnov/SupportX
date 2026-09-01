import os
from collections.abc import Mapping
from dataclasses import dataclass, fields


class ConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Texts:
    welcome: str = "👋 Hi! Send us your question and our team will reply right here."
    ticket_opened: str = "✅ Thanks! Your request has been received. We will get back to you as soon as possible."
    ticket_closed: str = "🔒 Your request has been closed. Just send a new message if you need anything else."
    no_open_ticket: str = "You have no open requests."
    delivery_failed: str = "❌ We could not deliver your message. Please try again later."
    slow_down: str = "⏳ You are sending messages too fast. Please wait a minute before writing again."
    desk_busy: str = "⏳ We are receiving a lot of new requests right now. Please write again in a few minutes."
    topic_title: str = "{full_name} · {user_id}"
    customer_card: str = (
        "👤 <b>{full_name}</b>\n"
        "ID: <code>{user_id}</code>\n"
        "Username: {username}\n\n"
        "/close — close the ticket\n"
        "/ban — block the customer\n"
        "/unban — unblock the customer\n"
        "/info — show this card\n\n"
        "Messages starting with <code>{note_prefix}</code> are internal notes and are not sent to the customer."
    )
    open_chat_button: str = "Open chat"
    no_username: str = "—"
    ticket_reopened_note: str = "🔓 The customer wrote again, the ticket is reopened."
    closed_by_customer_note: str = "🔒 The customer closed the ticket."
    closed_by_agent_note: str = "🔒 The ticket is closed."
    closed_by_inactivity_note: str = "🔒 The ticket was closed automatically after {days} days without messages."
    already_closed_note: str = "This ticket is already closed."
    not_delivered_note: str = "⚠️ This message could not be delivered to the customer."
    customer_blocked_bot_note: str = "⚠️ The customer blocked the bot, so the message was not delivered. The ticket is closed."
    customer_banned_note: str = "⛔ Customer <code>{user_id}</code> is blocked."
    customer_unbanned_note: str = "✅ Customer <code>{user_id}</code> is unblocked."
    customer_not_found_note: str = "Customer <code>{user_id}</code> was not found."
    unban_usage_note: str = "Usage: <code>/unban user_id</code>, or just <code>/unban</code> inside the customer's topic."


TEMPLATE_SAMPLE_VALUES = {"full_name": "", "user_id": 0, "username": "", "note_prefix": "", "days": 0}


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    support_group_id: int
    database_url: str
    internal_note_prefix: str
    auto_close_after_days: int
    customer_messages_per_minute: int
    new_tickets_per_minute: int
    log_level: str
    texts: Texts


def load_settings(environ: Mapping[str, str] = os.environ) -> Settings:
    return Settings(
        bot_token=_require(environ, "BOT_TOKEN"),
        support_group_id=_to_int("SUPPORT_GROUP_ID", _require(environ, "SUPPORT_GROUP_ID")),
        database_url=_require(environ, "DATABASE_URL"),
        internal_note_prefix=environ.get("INTERNAL_NOTE_PREFIX", "//"),
        auto_close_after_days=_to_int("AUTO_CLOSE_AFTER_DAYS", environ.get("AUTO_CLOSE_AFTER_DAYS", "7")),
        customer_messages_per_minute=_to_int(
            "CUSTOMER_MESSAGES_PER_MINUTE", environ.get("CUSTOMER_MESSAGES_PER_MINUTE", "30")
        ),
        new_tickets_per_minute=_to_int("NEW_TICKETS_PER_MINUTE", environ.get("NEW_TICKETS_PER_MINUTE", "20")),
        log_level=environ.get("LOG_LEVEL", "INFO").upper(),
        texts=_load_texts(environ),
    )


def _require(environ: Mapping[str, str], name: str) -> str:
    value = environ.get(name, "").strip()
    if not value:
        raise ConfigurationError(f"{name} is not set")
    return value


def _to_int(name: str, raw_value: str) -> int:
    try:
        return int(raw_value)
    except ValueError:
        raise ConfigurationError(f"{name} must be a whole number, got {raw_value!r}") from None


def _load_texts(environ: Mapping[str, str]) -> Texts:
    overrides = {
        text_field.name: environ[env_name]
        for text_field in fields(Texts)
        if (env_name := f"MSG_{text_field.name.upper()}") in environ
    }
    texts = Texts(**overrides)
    for text_field in fields(Texts):
        template = getattr(texts, text_field.name)
        try:
            template.format_map(TEMPLATE_SAMPLE_VALUES)
        except (KeyError, IndexError, ValueError) as error:
            raise ConfigurationError(f"MSG_{text_field.name.upper()} has an invalid placeholder: {error}") from None
    return texts
