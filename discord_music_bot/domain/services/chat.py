import asyncio
import openai
import json

from discord_music_bot.domain.history import download_history

functions = [
    {
        "name": "enqueue_song",
        "description": "Enqueue a song to play",
        "parameters": {
            "type": "object",
            "properties": {
                "query" : {
                    "type": "string",
                    "description": "Song URL or search query",
                }
            }
        }
    },
    {
        "name": "skip_song",
        "description": "Skip the current song",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_now_playing_song",
        "description": "Get the name and artist of the current song playing",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "pause_song",
        "description": "Pause the current song",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "resume_song",
        "description": "Resume the current song",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_song_queue",
        "description": "The the current queue of songs to play",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "leave",
        "description": "Leave the voice chat and stop all playing music",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
]

class ChatService:

    def __init__(self, bot, music_service):
        self.memory = 10
        self.bot = bot
        self._music_service = music_service

    async def answer(self, channel, question, user, guild):
        if not openai.api_key:
            return "Chat not enabled!"

        chat_history = await download_history(
            channel, limit=self.memory, download_images=False
        )

        return await self.create_completion(chat_history, question, user, guild, channel)

    async def create_completion(self, chat_history, question, user, guild, channel):
        history_prompt = ""
        chat_history["messages"].pop(0)

        for message in reversed(chat_history["messages"]):
            history_prompt += message["sender"]["name"] + " said: " + message["messageContent"] + "\n"


        data = await asyncio.to_thread(
            openai.ChatCompletion.create, model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content":
                        "You are a Discord bot that chats with users. Your name is " + self.bot.user.name
                        + ". Below is a transcript of "
                        + "the conversation so far:\n" + history_prompt
                },
                {"role": "user", "content": question}
            ],
            functions=functions)
    
        data = data["choices"][0]

        print(data)

        msg = data["message"]["content"]

        if "function_call" in data["message"]:
            call = data["message"]["function_call"]
            args = json.loads(call["arguments"])
            fun = call["name"]

            if fun == "enqueue_song":
                msg = await self._music_service.enqueue_song(args["query"], 0, user, guild, channel, False)
            elif fun == "get_now_playing_song":
                msg = self._music_service.get_now_playing_song(guild)
            elif fun == "skip_song":
                msg = await self._music_service.skip_song(guild)
            elif fun == "pause_song":
                msg = self._music_service.pause_song(guild)
            elif fun == "resume_song":
                msg = self._music_service.resume_song(guild)
            elif fun == "get_song_queue":
                msg = self._music_service.get_song_queue(guild)
            else:
                msg = self._music_service.leave(guild)

        return msg
