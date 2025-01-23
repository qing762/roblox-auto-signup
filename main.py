import re
import asyncio
import warnings
from datetime import datetime
from DrissionPage import Chromium, ChromiumOptions
from tqdm import TqdmExperimentalWarning
from tqdm.rich import tqdm
from lib.lib import Main


warnings.filterwarnings("ignore", category=TqdmExperimentalWarning)


async def main():
    lib = Main()
    port = ChromiumOptions().auto_port()

    print("Checking for updates...")
    await lib.checkUpdate()

    username = lib.usernamecreator()

    while True:
        passw = (
            input(
                "\033[1m"
                "\n(RECOMMENDED) Press enter in order to use the default password"
                "\033[0m"
                "\nIf you prefer to use your own password, do make sure that your password is strong enough.\nThis script has a built in password complexity checker.\nPassword: "
            )
            or "Qing762.chy"
        )
        if passw != "Qing762.chy":
            result = await lib.checkPassword(username, passw)
            print(result)
            if "Password is valid" in result:
                break
        else:
            break

    accounts = []

    while True:
        executionCount = input(
            "\nNumber of accounts to generate (Default: 1): "
        )
        try:
            executionCount = int(executionCount)
            break
        except ValueError:
            if executionCount == "":
                executionCount = 1
                break
            else:
                print("Please enter a valid number.")
    print()

    for x in range(int(executionCount)):
        bar = tqdm(total=100)
        bar.set_description(f"Initial setup completed [{x + 1}/{executionCount}]")
        bar.update(20)
        chrome = Chromium(addr_or_opts=port)
        page = chrome.get_tab(id_or_num=1)
        page.listen.start("https://mails.org", method="POST")
        page.get("https://mails.org")

        for _ in range(10):
            result = page.listen.wait()
            if result.url == "https://mails.org/api/email/generate":
                email = result.response.body["message"]
                break

        if not email:
            print("Failed to generate email. Exiting...")
            continue

        bar.set_description(f"Account generation process [{x + 1}/{executionCount}]")
        bar.update(20)

        try:
            tab = chrome.new_tab("https://www.roblox.com/CreateAccount")
            bdaymonthelement = tab.ele("#MonthDropdown")
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
            bdaydayelement = tab.ele("#DayDropdown")
            if datetime.now().day <= 31:
                if datetime.now().day <= 9:
                    bdaydayelement.select.by_value("0" + str(datetime.now().day))
                bdaydayelement.select.by_value(str(datetime.now().day))
            else:
                bdaydayelement.select.by_value("01")
            tab.ele("#YearDropdown").select.by_value(str(datetime.now().year - 19))
            tab.ele("#signup-username").input(username)
            tab.ele("#signup-password").input(passw)
            tab.ele("#signup-button").click()
            page.listen.start("https://mails.org", method="POST")
        except Exception as e:
            print(f"An error occured\n{e}")
        finally:
            bar.set_description(f"Signup process [{x + 1}/{executionCount}]")
            bar.update(30)
            tab.wait.url_change("https://www.roblox.com/home", timeout=float('inf'))
            tab.ele(".btn-primary-md btn-primary-md btn-min-width").click()
            tab.ele(". form-control input-field verification-upsell-modal-input").input(email)
            tab.ele(".modal-button verification-upsell-btn btn-cta-md btn-min-width").click()

            if tab.ele(".verification-upsell-text-body", timeout=60):
                link = None
                for _ in range(10):
                    result = page.listen.wait()
                    content = result.response.body["emails"]
                    if not content:
                        continue
                    for _, y in content.items():
                        if (
                            y["subject"]
                            == f"Roblox Email Verification: {username}"
                        ):
                            links = re.findall(
                                r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
                                y["body"],
                            )
                            for link in links:
                                if link.startswith(
                                    "https://www.roblox.com/account/settings/verify-email?ticket="
                                ):
                                    link = re.sub(r"</?[^>]+>", "", link)
                                    break
                        if link:
                            break
                    if link:
                        break
                if link:
                    bar.set_description(
                        f"Verifying email address [{x + 1}/{executionCount}]"
                    )
                    bar.update(20)
                    tab.get(link)
                    bar.set_description("Clearing cache and data")
                    bar.update(9)
                    tab.set.cookies.clear()
                    tab.clear_cache()
                    chrome.set.cookies.clear()
                    chrome.clear_cache()
                    chrome.quit()

                    accounts.append({"username": username, "email": email, "password": passw})

                    bar.set_description(f"Done [{x + 1}/{executionCount}]")
                    bar.update(1)
                    bar.close()
                    print()
                else:
                    print(
                        "Failed to find verification email. You may need to verify it manually. Skipping and continuing...\n"
                    )

    with open("accounts.txt", "a") as f:
        for account in accounts:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(
                f"Username: {account['username']}, Email: {account['email']}, Password: {account['password']} (Created at {timestamp})\n"
            )
    print("\033[1m" "Credentials:")

    for account in accounts:
        print(f"Username: {account['username']}, Email: {account['email']}, Password: {account['password']}")
    print("\033[0m" "\nCredentials saved to accounts.txt\nHave fun playing Roblox!")

if __name__ == "__main__":
    asyncio.run(main())
