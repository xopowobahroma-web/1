from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def mental_load_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i in range(1, 11):
        builder.button(text=str(i), callback_data=f"mental_load:{i}")
    builder.adjust(5)
    return builder.as_markup()

def thoughts_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Мысли были", callback_data="thoughts:yes")
    builder.button(text="Нет", callback_data="thoughts:no")
    return builder.as_markup()

def last_hour_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Код", callback_data="last_hour:code")
    builder.button(text="Бизнес-план", callback_data="last_hour:business")
    builder.button(text="Соцсети", callback_data="last_hour:social")
    builder.button(text="Отдыхал", callback_data="last_hour:rest")
    builder.adjust(2)
    return builder.as_markup()

def sleep_quality_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Провалился сразу", callback_data="sleep_quality:fast")
    builder.button(text="Долго засыпал", callback_data="sleep_quality:slow")
    builder.button(text="Просыпался", callback_data="sleep_quality:interrupted")
    return builder.as_markup()

def wakeup_reason_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Будильник", callback_data="wake_reason:alarm")
    builder.button(text="Сам", callback_data="wake_reason:self")
    builder.button(text="Кошмар", callback_data="wake_reason:nightmare")
    builder.button(text="Шум", callback_data="wake_reason:noise")
    builder.adjust(2)
    return builder.as_markup()