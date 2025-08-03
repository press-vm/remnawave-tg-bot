from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):

    waiting_for_broadcast_message = State()
    confirming_broadcast = State()
    waiting_for_promo_details = State()
    waiting_for_promo_code = State()
    waiting_for_promo_bonus_days = State()
    waiting_for_promo_max_activations = State()
    waiting_for_promo_validity_days = State()
    waiting_for_promo_edit_details = State()
    waiting_for_bulk_promo_quantity = State()
    waiting_for_bulk_promo_bonus_days = State()
    waiting_for_bulk_promo_max_activations = State()
    waiting_for_bulk_promo_validity_days = State()
    waiting_for_user_id_to_ban = State()
    waiting_for_user_id_to_unban = State()

    waiting_for_user_id_for_logs = State()
    
    # User management states
    waiting_for_user_search = State()
    waiting_for_subscription_days_to_add = State()
    waiting_for_direct_message_to_user = State()
