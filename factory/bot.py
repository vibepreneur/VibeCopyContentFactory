import asyncio
import json
import time
from pathlib import Path
from typing import Protocol
from .engine import Factory

class Gateway(Protocol):
    async def send(self,kind: str,payload: dict): ...

class FakeGateway:
    def __init__(self):
        self.messages=[]

    async def send(self,kind,payload):
        for path in payload.get('files',[]):
            if not Path(path).is_file():
                raise FileNotFoundError('Telegram delivery asset missing')
        self.messages.append({'kind':kind,**payload})

class Controller:
    def __init__(self,factory: Factory):
        self.factory=factory

    def authorized(self,user_id):
        return user_id in self.factory.config.admin_ids

    def command(self,user_id,text):
        if not self.authorized(user_id):
            return 'Доступ запрещён.'
        args=text.split()
        command=args[0].split('@')[0] if args else '/help'
        if command in ('/start','/help'):
            return 'Factory '+self.factory.config.mode+'\n/mode_a 10 — новые кандидаты\n/mode_b 10 — одобренная библиотека без AI\n/status — партии, проверки, ошибки и расходы'
        if command=='/status':
            return json.dumps(self.factory.status(),ensure_ascii=False,indent=2)
        if command in ('/mode_a','/mode_b'):
            if args[1:]!=['10']:
                return 'Используйте '+command+' 10'
            batch=self.factory.start_a() if command=='/mode_a' else self.factory.start_b()
            count=self.factory.db.one('SELECT count(*) n FROM batch_slots WHERE batch_id=?',(batch,))['n']
            return f'Партия {batch}: {count}/10 слотов. '+('Недостаточно одобренных уникальных материалов.' if count<10 else '')
        return 'Неизвестная команда. /help'

    def callback(self,user_id,data):
        if not self.authorized(user_id):
            return 'Доступ запрещён.'
        try:
            parts=data.split(':')
            if parts[0]=='c' and len(parts)==4:
                return self.factory.review_case(parts[2],{'a':'approve','r':'retry','x':'reject-final'}[parts[1]],int(parts[3]))
            if parts[0]=='v' and len(parts)==3:
                return self.factory.review_video(parts[2],{'a':'approve','r':'remake','x':'reject'}[parts[1]])
        except (KeyError,ValueError) as e:
            return str(e)
        return 'INVALID_CALLBACK'

async def flush_notifications(factory: Factory,gateway: Gateway):
    delivered=0
    for notification in factory.db.all("SELECT * FROM notifications WHERE status IN ('PENDING','FAILED') ORDER BY created_at"):
        try:
            if notification['kind']=='candidate':
                attempt=factory.db.one('SELECT * FROM processing_attempts WHERE request_id=?',(notification['entity_id'],))
                case=factory.db.one('SELECT * FROM cases WHERE id=?',(attempt['case_id'],))
                if case['processing_request_id']!=attempt['request_id']:
                    factory.db.execute("UPDATE notifications SET status='SUPERSEDED' WHERE id=?",(notification['id'],))
                    continue
                pair=factory.db.one('SELECT * FROM photo_pairs WHERE id=?',(case['pair_id'],))
                files=[str(factory.library.file(pair[k])) for k in ('original_asset_id','reference_asset_id')]
                if case['result_asset_id']:
                    files.append(str(factory.library.file(case['result_asset_id'])))
                buttons=[('✅ Принять',f"c:a:{case['id']}:{attempt['attempt_no']}")] if case['status']=='PENDING_REVIEW' else []
                if case['status']!='RECONCILIATION_REQUIRED':
                    buttons.append(('🔁 Переделать',f"c:r:{case['id']}:{attempt['attempt_no']}"))
                buttons.append(('❌ Отказ',f"c:x:{case['id']}:{attempt['attempt_no']}"))
                payload={'text':f"{factory.config.mode} · Case {case['id']} · попытка {attempt['attempt_no']} · {case['status']}",'files':files,'buttons':buttons}
            else:
                video=factory.db.one('SELECT * FROM video_jobs WHERE id=?',(notification['entity_id'],))
                payload={'text':f"{factory.config.mode} · Видео {video['id']} · финальная проверка",'files':[str(factory.library.file(video['final_asset_id']))],
                         'buttons':[(label,f"v:{action}:{video['id']}") for label,action in [('✅ Одобрить','a'),('♻️ Пересобрать','r'),('❌ Отклонить','x')]]}
            await gateway.send(notification['kind'],payload)
            factory.db.execute("UPDATE notifications SET status='SENT',error=NULL WHERE id=?",(notification['id'],))
            delivered+=1
        except Exception as e:
            factory.db.execute("UPDATE notifications SET status='FAILED',error=? WHERE id=?",(type(e).__name__+': '+str(e),notification['id']))
    return delivered

class TelegramGateway:
    def __init__(self,bot,admin_ids):
        self.bot,self.admin_ids=bot,admin_ids

    async def send(self,kind,payload):
        from aiogram.types import FSInputFile, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
        keyboard=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=label,callback_data=data)] for label,data in payload['buttons']])
        for admin in self.admin_ids:
            if kind=='candidate':
                media=[InputMediaPhoto(media=FSInputFile(p)) for p in payload['files']]
                if len(media)>=2:
                    await self.bot.send_media_group(admin,media)
                await self.bot.send_message(admin,payload['text'],reply_markup=keyboard)
            else:
                file=payload['files'][0]
                await self.bot.send_video(admin,FSInputFile(file),caption=payload['text'],supports_streaming=True)
                await self.bot.send_document(admin,FSInputFile(file),caption=payload['text'],reply_markup=keyboard)

def dispatcher(controller):
    from aiogram import Dispatcher
    dp=Dispatcher()
    @dp.message()
    async def message(msg):
        if msg.chat.type!='private':
            await msg.answer('Используйте личный чат с админ-ботом.')
            return
        try:
            result=controller.command(msg.from_user.id,msg.text or '/help')
        except Exception as e:
            result=str(e)
        for start in range(0,len(result),3500):
            await msg.answer(result[start:start+3500])
    @dp.callback_query()
    async def callback(query):
        if not query.message or query.message.chat.type!='private':
            await query.answer('Доступ запрещён.',show_alert=True)
            return
        result=controller.callback(query.from_user.id,query.data or '')
        await query.answer(result[:180])
    return dp

async def run_bot(factory):
    from aiogram import Bot
    if not factory.config.telegram_token or not factory.config.admin_ids:
        raise ValueError('Set FACTORY_TELEGRAM_TOKEN and FACTORY_ADMIN_USER_IDS locally')
    bot=Bot(factory.config.telegram_token)
    gateway=TelegramGateway(bot,factory.config.admin_ids)
    async def notify_loop():
        while True:
            await flush_notifications(factory,gateway)
            await asyncio.sleep(15)
    try:
        await asyncio.gather(dispatcher(Controller(factory)).start_polling(bot),notify_loop(),factory.run())
    finally:
        await bot.session.close()
