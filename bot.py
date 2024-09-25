from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
import asyncio
import os
from datetime import datetime

# Initialize bot with API token
API_TOKEN = '7458469423:AAG_3Mx21mZba8uxiZgQvw3QpGWw3k9ZHoc'  # Replace with your actual API token
BOT_USERNAME = "coco1_coin_bot"  # Replace with your bot's actual username
app = Application.builder().token(API_TOKEN).build()

# Define paths for balance and referral storage
BALANCE_FILE = "balance.txt"
REFERRAL_FILE = "referral.txt"
WITHDRAW_FILE = "withdrawals.txt"

# Define your primary and optional channel usernames
PRIMARY_CHANNEL = "Bins_Premium_account_Tricks"
OPTIONAL_CHANNEL = "bd71_earn_money"

# Referral reward and minimum withdrawal amount
REFERRAL_REWARD = 20
MIN_WITHDRAWAL_AMOUNT = 100

# Conversation states
WITHDRAWAL_AMOUNT, ACCOUNT_INFO = range(2)

# Create text files if they don't exist
for file in [BALANCE_FILE, REFERRAL_FILE, WITHDRAW_FILE]:
    if not os.path.exists(file):
        with open(file, 'w') as f:
            pass

# Read balance data from file
def get_balance(user_id):
    with open(BALANCE_FILE, 'r') as f:
        for line in f:
            user_data = line.strip().split(',')
            if str(user_id) == user_data[0]:
                return int(user_data[2])
    return 0

# Update balance in file
def update_balance(user_id, username, amount):
    balances = []
    found = False
    with open(BALANCE_FILE, 'r') as f:
        for line in f:
            user_data = line.strip().split(',')
            if str(user_id) == user_data[0]:
                balances.append(f"{user_id},{username},{int(user_data[2]) + amount}\n")
                found = True
            else:
                balances.append(line)
    if not found:
        balances.append(f"{user_id},{username},{amount}\n")

    with open(BALANCE_FILE, 'w') as f:
        f.writelines(balances)

# Store referral data
def store_referral(referrer, referred_user):
    with open(REFERRAL_FILE, 'a') as f:
        f.write(f"{referrer},{referred_user}\n")

# Store withdrawal details
def store_withdrawal(user_id, username, amount, method, account_number, request_text):
    with open(WITHDRAW_FILE, 'a') as f:
        f.write(f"{user_id},{username},{amount},{method},{account_number},{request_text},{datetime.now()}\n")

# Check if user has been referred (from start link)
async def handle_referral(referral_code, new_user_id):
    referrer_id = referral_code
    if referrer_id != str(new_user_id):  # Avoid self-referral
        # Add referral reward to the referrer's balance
        update_balance(referrer_id, f"User-{referrer_id}", REFERRAL_REWARD)
        store_referral(referrer_id, new_user_id)

# Function to generate the persistent menu with buttons
def get_main_menu():
    buttons = [
        ["Check Balance", "Withdraw"],
        ["Refer a Friend", "Help"],
        ["Join Optional Channel", "Visit Our Website"]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# /start command with referral link and persistent buttons
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name

    # Store the user in the balance file if not already present
    if get_balance(user_id) == 0:
        update_balance(user_id, username, 0)

    # Check if this is a referral link
    if context.args:
        referral_code = context.args[0]
        await handle_referral(referral_code, user_id)

    # Send welcome message with referral link and main menu
    await update.message.reply_text(
        f"Welcome, {username}! 👋\n\n"
        "Use the buttons below to manage your account:",
        reply_markup=get_main_menu()
    )

# Balance check function
async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    balance = get_balance(user_id)
    await update.message.reply_text(f"Your current balance is {balance} Taka.", reply_markup=get_main_menu())

# Withdrawal handler
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    balance = get_balance(user_id)
    if balance < MIN_WITHDRAWAL_AMOUNT:
        await update.message.reply_text(
            f"Your balance is less than {MIN_WITHDRAWAL_AMOUNT} Taka. Minimum withdrawal is {MIN_WITHDRAWAL_AMOUNT} Taka.",
            reply_markup=get_main_menu()
        )
        return ConversationHandler.END

    await update.message.reply_text(
        f"Enter the amount you want to withdraw (minimum {MIN_WITHDRAWAL_AMOUNT} Taka):"
    )
    return WITHDRAWAL_AMOUNT

async def withdrawal_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        amount = int(update.message.text.strip())
        if amount < MIN_WITHDRAWAL_AMOUNT or amount > get_balance(user_id):
            await update.message.reply_text(
                f"Invalid amount. Please enter an amount between {MIN_WITHDRAWAL_AMOUNT} Taka and your current balance ({get_balance(user_id)} Taka)."
            )
            return WITHDRAWAL_AMOUNT
        context.user_data['withdrawal_amount'] = amount
        await update.message.reply_text(
            "Please enter your account number or ID, and any additional information (e.g., reason for withdrawal):"
        )
        return ACCOUNT_INFO
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return WITHDRAWAL_AMOUNT

async def account_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    username = update.message.from_user.username or update.message.from_user.first_name
    request_text = update.message.text.strip()
    amount = context.user_data.get('withdrawal_amount')

    # Store the withdrawal data and add a 24-hour delay for processing
    store_withdrawal(user_id, username, amount, "Bank Transfer", "", request_text)
    await update.message.reply_text(
        f"Your withdrawal of {amount} Taka is being processed. Please be patient.\n\n"
        f"⚠️ Reminder: If you are not a member of our primary channel [{PRIMARY_CHANNEL}](https://t.me/{PRIMARY_CHANNEL}), you may not receive your payment.",
        reply_markup=get_main_menu()
    )

    # Deduct balance after withdrawal
    update_balance(user_id, username, -amount)

    # Simulate delay for withdrawal processing (24 hours)
    asyncio.create_task(process_withdrawal(update, user_id, amount))

    return ConversationHandler.END

async def process_withdrawal(update: Update, user_id: int, amount: int):
    await asyncio.sleep(24 * 60 * 60)  # 24 hours delay

    # Notify user about withdrawal completion
    try:
        await update.message.reply_text(
            f"Your withdrawal of {amount} Taka has been completed successfully ✅. You can continue chatting now!",
            reply_markup=get_main_menu()
        )
    except Exception as e:
        print(f"Failed to send withdrawal completion message to user {user_id}: {e}")

# Referral handler
async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    await update.message.reply_text(
        f"💸 **Your referral link:** https://t.me/{BOT_USERNAME}?start={user_id}\n"
        f"Share this link to refer friends and earn {REFERRAL_REWARD} Taka for each referral!",
        reply_markup=get_main_menu()
    )

# Help handler
async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "💡 **How to Use the Bot**:\n\n"
        f"1. **Check Balance**: See your current balance.\n"
        f"2. **Withdraw**: Withdraw money once you have at least {MIN_WITHDRAWAL_AMOUNT} Taka. *Note: You are encouraged to join our primary channel to ensure payment.*\n"
        "3. **Refer a Friend**: Share your referral link and earn 20 Taka for every friend who joins.\n"
        "4. **Visit Our Website**: Click the button below to visit our website.\n"
        "5. **Join Optional Channel**: Stay updated with additional news and offers."
    )
    await update.message.reply_text(help_text, reply_markup=get_main_menu())

# Button handler for all callbacks
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == 'Check Balance':
        await check_balance(update, context)
    elif text == 'Withdraw':
        return await withdraw(update, context)
    elif text == 'Refer a Friend':
        await refer(update, context)
    elif text == 'Help':
        await help_handler(update, context)
    elif text == 'Join Optional Channel':
        await update.message.reply_text(f"Join our optional channel: [Join here](https://t.me/{OPTIONAL_CHANNEL})", reply_markup=get_main_menu())
    elif text == 'Visit Our Website':
        await update.message.reply_text("Visit our website: https://www.zooz.digital/", reply_markup=get_main_menu())
    else:
        await update.message.reply_text("Unknown command. Please use the menu.", reply_markup=get_main_menu())
    return ConversationHandler.END

# Set up command handlers
app.add_handler(CommandHandler('start', start))

# Set up conversation handler for withdrawal process
conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex('^Withdraw$'), withdraw)],
    states={
        WITHDRAWAL_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdrawal_amount)],
        ACCOUNT_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, account_info)],
    },
    fallbacks=[MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler)],
)

app.add_handler(conv_handler)
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))

# Start the bot using asyncio.run
if __name__ == '__main__':
    print("Bot is running...")
    asyncio.run(app.run_polling())
