# SupportX

![Demo](demo.gif)

SupportX is a Telegram bot that turns a Telegram group into a simple help desk.

Your customers write to the bot in a private chat. Each customer gets their own topic in your team's group, and anything your team writes in that topic goes back to the customer. Customers only see the bot, never your team's personal accounts.

## What it does

* **One topic per customer.** A topic appears when a customer writes for the first time. If they come back later, the same topic reopens, so the whole history stays in one place.
* **Any kind of message.** Text, photos, videos, files, voice messages and stickers go both ways.
* **Internal notes.** Messages in a topic that start with `//` stay inside the group, so your team can discuss a request without the customer seeing it.
* **Only admins answer.** Only administrators of your support group can reply to customers or use commands. Other group members can read, but nothing they write reaches customers. If someone adds the bot to any other group, it leaves right away.
* **Spam protection.** A customer who sends too many messages in a minute is asked to slow down, and the number of new requests per minute is capped, so a flood of fake requests cannot bury your group.
* **Tidy workspace.** Requests with no new messages for 7 days close on their own. You can change the number of days or turn this off.
* **Your own wording.** Every message the bot sends can be rewritten in any language.

## Commands

**Customers** (in the private chat with the bot):

* `/start` shows the welcome message.
* `/close` closes their request.

**Support team** (inside a customer's topic):

* `/info` shows who the customer is, with a button that opens a chat with them.
* `/close` closes the request and tells the customer.
* `/ban` blocks the customer. The bot ignores everything they send after that.
* `/unban` unblocks the customer. Outside their topic, use `/unban` followed by the customer's ID.

## Setting it up

You will need:

* a bot token from [@BotFather](https://t.me/BotFather);
* a Telegram group with **Topics** turned on, where the bot is an administrator allowed to manage topics and pin messages;
* a PostgreSQL database;
* Python 3.10 or newer.

1. Download the project and install it:

   ```bash
   git clone https://github.com/VladislavKrasnov/SupportX.git
   cd SupportX
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill in the three required values:

   ```env
   BOT_TOKEN=your_bot_token_here
   SUPPORT_GROUP_ID=-100123456789
   DATABASE_URL=postgresql://user:password@localhost:5432/supportx
   ```

3. Start the bot:

   ```bash
   python -m bot
   ```

The bot creates its database tables on first start, so there is nothing else to set up.

## Settings

All settings go in the same `.env` file.

| Setting | What it does | Default |
| --- | --- | --- |
| `AUTO_CLOSE_AFTER_DAYS` | Days without messages before a request closes. `0` turns this off. | `7` |
| `INTERNAL_NOTE_PREFIX` | Messages starting with this stay inside the group. Leave it empty to turn notes off. | `//` |
| `CUSTOMER_MESSAGES_PER_MINUTE` | How many messages one customer can send per minute. `0` removes the limit. | `30` |
| `NEW_TICKETS_PER_MINUTE` | How many new requests can open per minute across all customers. `0` removes the limit. | `20` |
| `LOG_LEVEL` | How much the bot writes to its log. | `INFO` |

### Changing the bot's messages

Every message has a setting whose name starts with `MSG_`. For example, this sets the welcome message:

```env
MSG_WELCOME=👋 Здравствуйте! Напишите ваш вопрос, и мы ответим здесь.
```

<details>
<summary>All message settings</summary>

| Setting | Where it appears |
| --- | --- |
| `MSG_WELCOME` | Reply to `/start` |
| `MSG_TICKET_OPENED` | Sent to the customer when a request opens |
| `MSG_TICKET_CLOSED` | Sent to the customer when a request closes |
| `MSG_NO_OPEN_TICKET` | Sent when a customer uses `/close` with no open request |
| `MSG_DELIVERY_FAILED` | Sent when a customer's message could not be delivered |
| `MSG_SLOW_DOWN` | Sent when a customer writes too fast |
| `MSG_DESK_BUSY` | Sent when too many new requests arrive at once |
| `MSG_TOPIC_TITLE` | Name of a new topic |
| `MSG_CUSTOMER_CARD` | The customer card pinned in each topic and shown by `/info` |
| `MSG_OPEN_CHAT_BUTTON` | Label of the button on the customer card |
| `MSG_NO_USERNAME` | Shown on the card when the customer has no username |
| `MSG_TICKET_REOPENED_NOTE` | Posted in the topic when the customer writes again |
| `MSG_CLOSED_BY_CUSTOMER_NOTE` | Posted in the topic when the customer closes the request |
| `MSG_CLOSED_BY_AGENT_NOTE` | Posted in the topic when your team closes the request |
| `MSG_CLOSED_BY_INACTIVITY_NOTE` | Posted in the topic when a request closes on its own |
| `MSG_ALREADY_CLOSED_NOTE` | Reply to `/close` in a topic that is already closed |
| `MSG_NOT_DELIVERED_NOTE` | Reply when a team message could not reach the customer |
| `MSG_CUSTOMER_BLOCKED_BOT_NOTE` | Posted in the topic when the customer has blocked the bot |
| `MSG_CUSTOMER_BANNED_NOTE` | Reply to `/ban` |
| `MSG_CUSTOMER_UNBANNED_NOTE` | Reply to `/unban` |
| `MSG_CUSTOMER_NOT_FOUND_NOTE` | Reply to `/unban` with an unknown ID |
| `MSG_UNBAN_USAGE_NOTE` | Reply to `/unban` used the wrong way |

Some messages can include details in curly braces: `{full_name}`, `{username}` and `{user_id}` in the topic title and customer card, `{note_prefix}` in the customer card, `{user_id}` in ban messages and `{days}` in the auto-close note. The bot refuses to start if a message uses a placeholder it does not know, so a typo cannot break it later.

</details>

## License

SupportX is released under the [Apache License 2.0](LICENSE).
