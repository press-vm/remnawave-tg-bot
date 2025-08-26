from aiogram.fsm.state import State, StatesGroup


class UserPromoStates(StatesGroup):
    waiting_for_promo_code = State()


class UserSupportStates(StatesGroup):
    waiting_for_message = State()
