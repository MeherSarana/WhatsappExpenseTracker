import datetime
import textwrap
import pyotp

# to parse the user's expenses into a List-of-tuples like [('Apple 5 kg', 50), ('chicken 65', 65)].
def parse_expense_message_by_line(body):
    # Split the message into lines and strip extra spaces
    lines = body.strip().split('\n')
    result = []
    for line in lines:
        line = line.strip()  # remove leading/trailing spaces
        if not line:  # skip empty lines
            continue
        tokens = line.split()
        amount=None
        len_tokens=len(tokens)
        # now for sample tokens=('apple', '50'), check if last value is a digit, if yes, simply consider it as amount.
        if tokens[len_tokens-1].isdigit():
            amount=tokens.pop(len_tokens-1)
            item=" ".join(tokens)
            result.append((item, int(amount)))
            continue
        words = []
        for token in tokens:
            if token.isdigit():
                amount = int(token)
            else:
                words.append(token)
        # Join all words as a single item
        item = " ".join(words)
        if item and amount is not None:
            result.append((item, amount))
    return result
    # sample:
    # body="""Apple 5 kg 50
    # rice 2 kg 60
    # 80      kiwi
    # chicken 65 65
    # """
    # sample result: [('Apple 5 kg', 50), ('rice 2 kg', 60), ('kiwi', 80), ('chicken 65', 65)]
    # still dosen't handle '120 chicken 65' , it gives ('120 chicken', 65)

# Used to format the expenses(list-of-tuples) into a table-structure - used to send as reply to user for expenses confirmation.
def format_expense_message(expense_list):
    col_width = 19
    lines = [f"{'Item-name'.ljust(col_width)}Amount", '-' * (col_width + 6)]
    for item, amt in expense_list:
        wrapped = textwrap.wrap(item, width=col_width)
        # when sample item='word1 word2 word3 word4' then wrapped stores a List-of-Strings like ['word1 word2 word3', 'word4']
        for i, line in enumerate(wrapped):
            if i == 0:
                lines.append(f"{line.ljust(col_width)}{amt}")
            else:
                lines.append(line.ljust(col_width))
    return "```\n" + "\n".join(lines) + "\n```"
    # Joins all lines in the lines(variable having the list of strings) into a single string using \n (new line character).
    # "```\n" and "\n```" are used to format the string to monospace-format, suitable for whatsapp chat.

    #Sample return value:
    # Item-name         Amount
    # ------------------------
    # apple             50
    # word1 word2 word3 60
    # word4              
    # kiwi              70

# sample input: "whatsapp:+91xxxxxxxxxx" || sample output: "+91xxxxxxxxxx"
def clean_number(raw_number):
    if raw_number.startswith("whatsapp:"):
        return raw_number.replace("whatsapp:","")
    return raw_number

# Used to send the helper instructions - called when user sends /help in whatsapp
def handle_help():
    return (
        "Hi! Here are the commands you can use:\n"
        "/help — view all available commands\n"
        "/totalexpenseuntilnow — get today’s total and item breakdown\n"
        "/categorize_items — get today’s category-wise expense summary\n"
        "/delete_account — delete your account & all expenses (requires confirmation)\n"
        # "📌 Examples of adding expenses:\n"
        "📌 Guidelines-Examples for sending expenses:\n"
        # "Apple 50\n"
        # "50 Banana"
        "Format:\n"
        "Item name (along with quantity - optional) followed by amount.\n"
        "Each new entry must start on a new line.\n"
        # "\r{Item name} \r{Quantity}(Optional) \r{Amount}\n"
        "Apple 50 ✅\n"
        # "50 Apple ✅\n\n"
        "Wheat 5kg 100 ✅\n"
        # "100 Wheat 5kg ✅\n\n"
        "Wheat 5 kg 100 ✅"
        # "100 Wheat 5 kg ❌"
    )

# Used to fetch the entire day's (12-hours) epoch-time range.
def get_today_epoch_range():
    """Return start and end epoch timestamps for today"""
    now = datetime.datetime.now()
    start_of_day = datetime.datetime(now.year, now.month, now.day, 0, 0, 0)
    end_of_day = datetime.datetime(now.year, now.month, now.day, 23, 59, 59)
    return int(start_of_day.timestamp()), int(end_of_day.timestamp())

# To fetch current current epoch time
def current_epoch_time():
    return int(datetime.datetime.now().timestamp())

# To generate a base32 string, to be assigned(only once) to a new user in supabase.
def generate_TOTP_secret():
    return pyotp.random_base32()