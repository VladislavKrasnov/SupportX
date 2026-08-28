import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Config:
    bot_token: str
    support_group_id: int
    database_url: str
    msg_start: str
    msg_ticket_created: str
    msg_ticket_closed: str
    msg_unsupported: str
    msg_user_blocked: str

def load_config() -> Config:
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise ValueError("BOT_TOKEN is missing")
        
    support_group_id_str = os.getenv("SUPPORT_GROUP_ID")
    if not support_group_id_str:
        raise ValueError("SUPPORT_GROUP_ID is missing")
        
    return Config(
        bot_token=bot_token,
        support_group_id=int(support_group_id_str),
        database_url=os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/supportx"),
        msg_start=os.getenv("MSG_START", "Welcome to support. Send your message."),
        msg_ticket_created=os.getenv("MSG_TICKET_CREATED", "Your ticket has been created. Please wait for an agent."),
        msg_ticket_closed=os.getenv("MSG_TICKET_CLOSED", "Your ticket has been closed."),
        msg_unsupported=os.getenv("MSG_UNSUPPORTED", "We encountered an error."),
        msg_user_blocked=os.getenv("MSG_USER_BLOCKED", "User has blocked the bot. Message not delivered.")
    )

config = load_config()
