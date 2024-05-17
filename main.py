import browsers
from datetime import datetime
from DrissionPage import ChromiumPage
from lib.lib import Main

lib = Main()

print("\nEnsuring Chrome availability...")

if browsers.get("chrome") is None:
    print(
        "\nChrome is required for this tool. Please install it via:\nhttps://google.com/chrome"
    )
    exit()
else:
    passw = input(
        "\nInput your password for your account.\nIt is recommended for you to stay with the default password, ignore this and press enter\nIf you prefer to input your own password, you might need to manually verify the password strength at https://roblox.com/ yourself.\nPassword: "
    )

    if passw == "":
        passw = "Qing762.chy"
    else:
        passw = passw

    accounts = []

    while True:
        executionCount = input(
            "\nHow many accounts do you want to create?\nIf nothing is entered, the script will stick to the default value (1)\nAmount: "
        )
        if executionCount == "":
            executionCount = 1
            break
        else:
            try:
                executionCount = int(executionCount)
                break
            except ValueError:
                print("Invalid number given. Please enter a valid number.")

    print(
        "\nDue to the inner workings of the module, it is needed to browse programmatically.\nNEVER use the gui to navigate (Using your keybord and mouse) as it will causes POSSIBLE DETECTION!\nThe script will do the entire job itself.\n"
    )

    for x in range(int(executionCount)):
        page = ChromiumPage()
        try:
            page.get("https://www.roblox.com/CreateAccount")
            bdaymonthelement = page.ele("#MonthDropdown")
            if datetime.now().month == 1:
                bdaymonthelement.select.by_value("Jan")
            elif datetime.now().month == 2:
                bdaymonthelement.select.by_value("Feb")
            elif datetime.now().month == 3:
                bdaymonthelement.select.by_value("Mar")
            elif datetime.now().month == 4:
                bdaymonthelement.select.by_value("Apr")
            elif datetime.now().month == 5:
                bdaymonthelement.select.by_value("May")
            elif datetime.now().month == 6:
                bdaymonthelement.select.by_value("Jun")
            elif datetime.now().month == 7:
                bdaymonthelement.select.by_value("Jul")
            elif datetime.now().month == 8:
                bdaymonthelement.select.by_value("Aug")
            elif datetime.now().month == 9:
                bdaymonthelement.select.by_value("Sep")
            elif datetime.now().month == 10:
                bdaymonthelement.select.by_value("Oct")
            elif datetime.now().month == 11:
                bdaymonthelement.select.by_value("Nov")
            elif datetime.now().month == 12:
                bdaymonthelement.select.by_value("Dec")
            else:
                bdaymonthelement.select.by_value("Jan")
            bdaydayelement = page.ele("#DayDropdown")
            if datetime.now().day <= 31:
                bdaydayelement.select.by_value(str(datetime.now().day))
            else:
                bdaydayelement.select.by_value("1")
            page.ele("#YearDropdown").select.by_value(str(datetime.now().year - 19))
            username = lib.usernamecreator()
            page.ele("#signup-username").input(username)
            page.ele("#signup-password").input(passw)
            page.ele("#signup-button").click()
        except Exception as e:
            print(f"An error occured\n{e}")
        finally:
            lib.waitUntilUrl(page, "https://www.roblox.com/home")
            page.set.cookies.clear()
            page.clear_cache()
            page.quit()
            accounts.append({"username": username, "password": passw})

    with open("accounts.txt", "a") as f:
        for account in accounts:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(
                f"Username: {account['username']}, Password: {account['password']} (Created at {timestamp})\n"
            )
    print("\nAll accounts have been created. Here are the accounts' details:\n")
    for account in accounts:
        print(f"Username: {account['username']}, Password: {account['password']}")
    print("\nThey have been saved to the file accounts.txt.\nHave fun playing Roblox!")
