# SupportX

![Demo](demo.gif)

Welcome to **SupportX**, the ultimate, high-performance solution for seamless customer support via Telegram. 

Designed exclusively for high-load production environments, SupportX bridges the gap between your users and your support agents. It creates an intuitive, instant connection where users can send messages directly to your bot, and your team can efficiently reply from a single, organized Telegram group using forum topics.

## Why Choose SupportX?

*   **Zero Latency Operations:** Engineered with an asynchronous architecture to guarantee split-second responses even under extreme load.
*   **Privacy First:** Built secure-by-default to ensure that all user interactions are fully protected.
*   **Frictionless Setup:** Deploys in under 5 minutes with an intuitive configuration structure. 
*   **Clutter-Free Support Group:** Automatically organizes individual user requests into dedicated forum topics. Topics are only generated when a user *actually* asks a question, keeping your support workspace flawlessly clean.
*   **Universal Media Support:** Seamlessly transfers text, images, videos, documents, and voice notes between users and agents.

## Quick Start Guide

You don't need to be an engineer to deploy SupportX. Just follow these simple steps to get your professional support system online immediately.

### 1. Prerequisites
*   Python 3.10 or newer installed on your server.
*   A running PostgreSQL database.
*   A Bot Token from [@BotFather](https://t.me/BotFather).
*   A Telegram Group with **Topics Enabled** to act as your support hub.

### 2. Installation
Clone the repository and install the lightning-fast dependencies:

```bash
git clone https://github.com/VladislavKrasnov/SupportX.git
cd SupportX
pip install -r requirements.txt
```

### 3. Configuration
Rename `.env.example` to `.env` and fill in your details:

```env
BOT_TOKEN=your_bot_token_here
SUPPORT_GROUP_ID=-100123456789
DATABASE_URL=postgresql://user:password@localhost:5432/supportx
AUTO_CLOSE_TOPICS_DAYS=7
```

You can fully customize the automated messages in the same `.env` file to match your brand's voice.
Set `AUTO_CLOSE_TOPICS_DAYS=0` to disable auto-closing of inactive topics.

### Commands

**For Users:**
* `/start` - Start interacting with the bot
* `/close` - Close your current support ticket

**For Admins (in Support Group):**
* `/info` - Get user information (ID, Username, quick contact link)
* `/ban` - Ban a user and prevent them from sending more messages
* `/unban <user_id>` - Unban a user

### 4. Launch
Ignite the engine:

```bash
python -m bot
```

Your elite customer support bot is now fully operational!

## License
SupportX is released under the [Apache License 2.0](LICENSE).
