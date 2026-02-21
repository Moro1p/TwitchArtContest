from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.type import AuthScope, ChatEvent
from twitchAPI.chat import Chat, EventData, ChatMessage, ChatSub, ChatCommand
import asyncio
import time
import os
from dotenv import load_dotenv


class TwitchBot:
    def __init__(self):
        load_dotenv()
        self.app_id = os.getenv('TWITCH_APP_ID')
        self.app_secret = os.getenv('TWITCH_APP_SECRET')
        self.user_scope = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT]
        self.target_channel = 'leoshaya'
        self.poll_dict = dict()
        self.poll_in_progress = False
        self.poll_art_id = None
        asyncio.run(self.run())

    async def on_ready(self, ready_event: EventData):
        print('Bot is ready for work, joining channels')
        await ready_event.chat.join_room(self.target_channel)


    async def on_message(self, msg: ChatMessage):
        if not self.poll_in_progress:
            return
        if msg.text.isdigit() and (1 <= int(msg.text) <= 10):
            self.poll_dict[msg.user.id] = int(msg.text)
            print(f"User {msg.user.id} typed {msg.text}")

    def CalculateAverageScore(self):
        if not self.poll_dict:
            print("No Scores")
            return -1
        summary_score = 0
        for score in self.poll_dict.values():
            summary_score += score
        score_count = len(self.poll_dict)
        self.poll_dict = dict()
        return summary_score / score_count

    async def stop_bot(self, twitch, chat):
        await chat.stop()
        await twitch.close()

    async def run(self):
        twitch = await Twitch(self.app_id, self.app_secret)
        auth = UserAuthenticator(twitch, self.user_scope)
        token, refresh_token = await auth.authenticate()
        await twitch.set_user_authentication(token, self.user_scope, refresh_token)

        chat = await Chat(twitch)

        chat.register_event(ChatEvent.READY, self.on_ready)
        chat.register_event(ChatEvent.MESSAGE, self.on_message)

        chat.start()
        await twitch.close()
    
    def stop(self):
        loop = asyncio.get_running_loop()
        loop.stop()

