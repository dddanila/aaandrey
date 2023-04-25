import asyncio
import logging
import openai
from aiohttp import ClientSession
from models import AssistantMessage, Conversation, Message, SystemMessage, UserMessage
from typing import cast

class GPTClient:
  def __init__(self, api_key: str,  max_message_count: int|None):
    self.__max_message_count = max_message_count

    openai.api_key = api_key
    openai.aiosession.set(ClientSession(trust_env=True))

  async def complete(self, conversation: Conversation, user_message: UserMessage, sent_msg_id: int, system_message: SystemMessage|None) -> AssistantMessage:
    logging.info(f"Completing message for conversation {conversation.id}, message: '{user_message}'")

    logging.debug(f"Current conversation for chat {conversation.id}: {conversation}")

    text = await self.__request(([system_message] if system_message else []) + conversation.messages)
    assistant_message = AssistantMessage(sent_msg_id, text, user_message.id)

    conversation.messages.append(assistant_message)

    logging.info(f"Completed message for chat {conversation.id}, message: '{assistant_message}'")

    if conversation.title is None and len(conversation.messages) < 3:
      async def set_title(conversation: Conversation):
        prompt = 'You are a title generator. You will receive one or multiple messages of a conversation. You will reply with only the title of the conversation without any punctuation mark either at the begining or the end.'
        messages = [SystemMessage(prompt)] + conversation.messages

        title = await self.__request(messages)
        conversation.title = title

        logging.info(f"Set title for conversation {conversation}: '{title}'")

      asyncio.create_task(set_title(conversation))

    return assistant_message

  def new_conversation(self, conversation_id: int, user_message: UserMessage) -> Conversation:
    conversation = Conversation(conversation_id, None, user_message.timestamp, [user_message])

    if self.__max_message_count and len(conversation.messages) > self.__max_message_count:
      conversation.messages = conversation.messages[self.__max_message_count:]

    return conversation

  async def __request(self, messages: list[Message]) -> str:
    task = openai.ChatCompletion.acreate(
      model='gpt-3.5-turbo',
      messages=[{'role': message.role, 'content': message.content} for message in messages],
    )
    response = await asyncio.wait_for(task, 500)
    return cast(dict, response)['choices'][0]['message']['content']
