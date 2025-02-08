import asyncio
import warnings
from datetime import datetime
from DrissionPage import Chromium, ChromiumOptions
from DrissionPage.common import wait_until
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
        page.get("https://mail.tm/en")
        page.ele(
            ".rounded-[calc(var(--ui-radius)*1.5)] font-medium inline-flex items-center "
            "focus:outline-hidden disabled:cursor-not-allowed aria-disabled:cursor-not-allowed "
            "disabled:opacity-75 aria-disabled:opacity-75 transition-colors px-2.5 py-1.5 text-sm "
            "gap-1.5 text-[var(--ui-primary)] hover:text-[var(--ui-primary)]/75 disabled:text-[var(--ui-primary)] "
            "aria-disabled:text-[var(--ui-primary)] focus-visible:ring-2 focus-visible:ring-inset "
            "focus-visible:ring-[var(--ui-primary)] group flex-1 justify-between"
        ).click()
        while True:
            email = page.ele('xpath://*[@id="reka-dropdown-menu-content-v-1-9"]/div[1]/div/div/p[2]').text
            emailPassword = page.ele('xpath://*[@id="reka-dropdown-menu-content-v-1-9"]/div[1]/div/div/p[3]/span').text
            if email != "..." and emailPassword != "...":
                break
        bar.set_description(f"Account generation process [{x + 1}/{executionCount}]")
        bar.update(20)
        
        try:
            tab = chrome.new_tab("https://www.roblox.com/CreateAccount")
            bdaymonthelement = tab.ele("#MonthDropdown")
            currentMonth = datetime.now().strftime("%b")
            bdaymonthelement.select.by_value(currentMonth)
            bdaydayelement = tab.ele("css:DayDropdown")
            currentDay = datetime.now().day
            if currentDay <= 9:
                bdaydayelement.select.by_value(f"0{currentDay}")
            else:
                bdaydayelement.select.by_value(str(currentDay))
            currentYear = datetime.now().year - 19
            tab.ele("#YearDropdown").select.by_value(str(currentYear))
            tab.ele("#signup-username").input(username)
            tab.ele("#signup-password").input(passw)
            tab.ele("#signup-button").click()
        except Exception as e:
            print(f"An error occurred\n{e}")
        finally:
            bar.set_description(f"Signup process [{x + 1}/{executionCount}]")
            bar.update(30)
            tab.wait.url_change("https://www.roblox.com/home", timeout=float('inf'))
            tab.ele(".btn-primary-md btn-primary-md btn-min-width").click()
            tab.ele(". form-control input-field verification-upsell-modal-input").input(email)
            tab.ele(".modal-button verification-upsell-btn btn-cta-md btn-min-width").click()

            if tab.ele(".verification-upsell-text-body", timeout=60):
                link = None
                mail = page.ele(".group block transition hover:bg-gray-50 focus:outline-none dark:focus:bg-gray-900/50 dark:hover:bg-gray-900/50")
                wait_until(
                    lambda: mail,
                    timeout=10
                )
                page.get(mail.attr("href"))
                link = page.ele('xpath:/html/body/center/div/table/tbody/tr/td/table/tbody/tr/td/table/tbody/tr/td/table/tbody/tr/td/table[10]/tbody/tr/td/table/tbody/tr/td/a').attr("href")
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

                    accounts.append({"username": username, "password": passw, "email": email, "emailPassword": emailPassword})

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
                f"Username: {account['username']}, Password: {account['password']}, Email: {account['email']}, Email Password: {account['emailPassword']} (Created at {timestamp})\n"
            )
    print("\033[1m" "Credentials:")

    for account in accounts:
        print(f"Username: {account['username']}, Password: {account['password']}, Email: {account['email']}, Email Password: {account['emailPassword']}")
    print("\033[0m" "\nCredentials saved to accounts.txt\nHave fun playing Roblox!")

if __name__ == "__main__":
    asyncio.run(main())
