from datetime import datetime, timezone
import pytest
from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import SendMessage, SendVideo, SendDocument, SendMediaGroup, AnswerCallbackQuery
from aiogram.types import Message, Chat, User, Update, CallbackQuery
from factory.bot import Controller, TelegramGateway, dispatcher

class RecordingSession(BaseSession):
    def __init__(self):
        super().__init__();self.requests=[]
    async def close(self):
        pass
    async def stream_content(self,*args,**kwargs):
        yield b''
    async def make_request(self,bot,method,timeout=None):
        self.requests.append(method)
        if isinstance(method,AnswerCallbackQuery):
            return True
        message=Message(message_id=len(self.requests),date=datetime.now(timezone.utc),chat=Chat(id=int(method.chat_id),type='private'))
        return [message]*len(method.media) if isinstance(method,SendMediaGroup) else message

async def test_actual_aiogram_routing_and_allowlist(factory):
    session=RecordingSession()
    bot=Bot('123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijk',session=session)
    dp=dispatcher(Controller(factory))
    for i,(user,command) in enumerate(((7,'/mode_a 10'),(42,'/start'),(42,'/mode_a 10')),1):
        message=Message(message_id=i,date=datetime.now(timezone.utc),chat=Chat(id=user,type='private'),from_user=User(id=user,is_bot=False,first_name='Test'),text=command)
        await dp.feed_update(bot,Update(update_id=i,message=message))
        if user==7:
            assert factory.db.all('SELECT * FROM batches')==[]
    assert len(factory.db.all('SELECT * FROM batches'))==1
    assert len(session.requests)==3 and all(isinstance(r,SendMessage) for r in session.requests)
    assert session.requests[0].text=='Доступ запрещён.'
    await bot.session.close()

async def test_actual_telegram_delivery_methods_are_mocked(factory):
    session=RecordingSession()
    bot=Bot('123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijk',session=session)
    gateway=TelegramGateway(bot,(42,))
    files=[str(factory.library.file(a['id'])) for a in factory.db.all("SELECT id FROM assets WHERE type='original' LIMIT 3")]
    await gateway.send('candidate',{'files':files,'text':'MOCK review','buttons':[('Approve','c:a:example:1')]})
    await gateway.send('video',{'files':[files[0]],'text':'MOCK master','buttons':[('Approve','v:a:example')]})
    assert [type(m) for m in session.requests]==[SendMediaGroup,SendMessage,SendVideo,SendDocument]
    assert all(m.chat_id==42 for m in session.requests)
    await bot.session.close()
