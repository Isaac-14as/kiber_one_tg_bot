from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message, BotCommand, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
import re
import gspread
from datetime import datetime
import pytz
import os

from dotenv import load_dotenv


load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
MENAGER = int(os.getenv('MENAGER'))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()

gc = gspread.service_account(filename='creads.json')
wks_all = gc.open("kiber_one_bot").sheet1
wks_users = gc.open("kiber_one_bot").worksheet('Все_пользователи')


USERS = {}


class Form(StatesGroup):
    waiting_phone_number = State()
    waiting_first_name = State()
    waiting_new_start_text = State()


@router.callback_query(F.data)
async def button_callback(callback_query: CallbackQuery, state: FSMContext):
    message = callback_query.message
    data = callback_query.data
    if data in ('Раменское', 'Люберцы', 'Жуковский'):
        utc_now = datetime.now(pytz.utc)
        moscow_tz = pytz.timezone("Europe/Moscow")
        moscow_time = utc_now.astimezone(moscow_tz)
        USERS[callback_query.from_user.id] = {
                      'city': data,
                      'username': callback_query.from_user.username,
                      'age': None,
                      'phone': None,
                      'date': moscow_time.strftime("%d-%m-%Y"),
                      'time': moscow_time.strftime("%H:%M"),
                      'first_name': None,
                      'source': 'TG'
                      }
        age_menu = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"6-8 лет", callback_data=f"6-8")],
                [InlineKeyboardButton(text=f"9-11 лет", callback_data=f"9-11")],
                [InlineKeyboardButton(text=f"12-14 лет", callback_data=f"12-14")]])
        await message.answer(text="Укажите <b>возраст вашего ребенка</b>, чтобы мы подобрали для него оптимальную группу👇", parse_mode=ParseMode.HTML, reply_markup=age_menu)
        await state.clear()
        return
    
    if data in ('6-8', '9-11', '12-14'):
        USERS[callback_query.from_user.id]['age'] = data
        await message.answer(text="Как к <b>Вам может обращаться</b> менеджер?", parse_mode=ParseMode.HTML)
        await state.set_state(Form.waiting_first_name)
        return
    
    if data == 'yes':
        await state.clear()
        await message.answer(text="Ваши данные записаны, <b>ожидайте звонка</b>!", parse_mode=ParseMode.HTML)
        all_data = wks_all.get_all_values()[1::]
        all_data.append(list(USERS[callback_query.from_user.id].values()))
        wks_all.update(all_data, 'A2')
        wks_all.format(f'A2:H{len(all_data) + 1}', {
            "borders": {
                "top": {"style": "SOLID"},
                "bottom": {"style": "SOLID"},
                "left": {"style": "SOLID"},
                "right": {"style": "SOLID"}
            }
        })

        try:
            info = f'''<b>Город:</b> {USERS[callback_query.from_user.id]['city']}
<b>ТГ:</b> @{USERS[callback_query.from_user.id]['username']}
<b>Возраст:</b> {USERS[callback_query.from_user.id]['age']} лет
<b>Имя представителя:</b> {USERS[callback_query.from_user.id]['first_name']}
<b>Телефон:</b> {USERS[callback_query.from_user.id]['phone']}
<b>Дата/время:</b> {USERS[callback_query.from_user.id]['date']} {USERS[callback_query.from_user.id]['time']}'''
            await bot.send_message(chat_id=MENAGER, parse_mode=ParseMode.HTML, text=info)
        except Exception as e:
            print(f"Ошибка при отправке сообщения пользователю {MENAGER}: {e}")
        return
    
    if data == 'no':
        await state.clear()
        await callback_sing_up(message, state)
        return





@router.message(Form.waiting_first_name)
async def waiting_first_name(message: Message, state: FSMContext):
    USERS[message.from_user.id]['first_name'] = message.text
    text = '''Спасибо! Остался последний шаг😊

Укажите <b>Ваш номер телефона</b>. Наш администратор свяжется с Вами🤗
'''
    await message.answer(text=text, parse_mode=ParseMode.HTML)
    await state.set_state(Form.waiting_phone_number)
    return



@router.message(Form.waiting_phone_number)
async def get_phone_number(message: Message, state: FSMContext):
    pattern = r'^(\+7|8)[\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}$'
    if re.match(pattern, message.text) is None:
        await message.answer("Вы ввели <b>неккоректный номер телефона</b>. Пожалуйста, введите номер телефона <b>еще раз</b>:", parse_mode=ParseMode.HTML)
        return
    USERS[message.from_user.id]['phone'] = message.text

    text = f'''Пожалуйста, проверьте Ваши данные. 

Если все правильно, смело нажимайте <b>"Записаться!"</b> и ждите звонка нашего менеджера😊.

    • <b>Город:</b> {USERS[message.from_user.id]['city']}
    • <b>Возраст:</b> {USERS[message.from_user.id]['age']} лет
    • <b>Имя представителя:</b> {USERS[message.from_user.id]['first_name']}
    • <b>Телефон:</b> {USERS[message.from_user.id]['phone']}

Если ошиблись, нажмите <b>"Перепройти("</b> и пройдите регистрацию заново.
            '''
    answer_menu = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"Перепройти(", callback_data=f"no"),
                InlineKeyboardButton(text=f"Записаться!", callback_data=f"yes")]])
    
    await message.answer(text=text, parse_mode=ParseMode.HTML, reply_markup=answer_menu)
    await state.clear()
    return

    


@router.message(Command(commands=['start']))
async def callback_start(message: Message, state: FSMContext):
    utc_now = datetime.now(pytz.utc)
    moscow_tz = pytz.timezone("Europe/Moscow")
    moscow_time = utc_now.astimezone(moscow_tz)
    all_data = wks_users.get_all_values()[1::]
    all_data.append([message.from_user.id, message.from_user.username, moscow_time.strftime("%d-%m-%Y"), moscow_time.strftime("%H:%M")])
    wks_users.update(all_data, 'A2')

    await state.clear()
    if message.from_user.id == MENAGER:
        commands = [
            BotCommand(command='start', description='Запустить бота'),
            BotCommand(command='sign_up', description='Записаться на пробное занятие'),
            BotCommand(command='set_start_text', description='Изменить содержание поста'),
            ]
        await bot.set_my_commands(commands)
    with open('start_text.txt', 'r', encoding='utf-8') as file:
        await message.answer_photo(photo=FSInputFile('start.jpeg'), caption=file.read().strip(), parse_mode=ParseMode.HTML)
    await callback_sing_up(message, state)
    return


@router.message(Command(commands=['sign_up']))
async def callback_sing_up(message: Message, state: FSMContext):
    await state.clear()
    city_menu = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"Раменское", callback_data=f"Раменское")],
                [InlineKeyboardButton(text=f"Люберцы", callback_data=f"Люберцы")],
                [InlineKeyboardButton(text=f"Жуковский", callback_data=f"Жуковский")]])
    await message.answer(text="Чтобы записаться выберите <b>город</b> 👇", parse_mode=ParseMode.HTML, reply_markup=city_menu)
    return



@router.message(Command(commands=['set_start_text']))
async def callback_set_start_text(message: Message, state: FSMContext):
    with open('start_text.txt', 'r', encoding='utf-8') as file:
        await message.answer(text=file.read().strip(), parse_mode=ParseMode.HTML)
        await state.set_state(Form.waiting_new_start_text)
        return



@router.message(Form.waiting_new_start_text)
async def get_new_start_text(message: Message, state: FSMContext):
    if message.text not in ('/start', '/sign_up', '/set_start_text'):
        with open('start_text.txt', 'w', encoding='utf-8') as file:
            file.write(message.text)
            await message.answer(text="Текст успешно обновлен", parse_mode=ParseMode.HTML)
        return



async def set_commands(bot: Bot):
    await bot.set_my_commands([
        BotCommand(command='start', description='Запустить бота'),
        BotCommand(command='sign_up', description='Записаться на пробное занятие'),
    ])


async def on_startup(dispatcher: Dispatcher, bot: Bot):
    await set_commands(bot)

if __name__ == '__main__':
    dp.include_router(router)
    dp.startup.register(on_startup)
    dp.run_polling(bot, skip_updates=True)