import asyncio
import warnings
import json
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
            result = await lib.checkPassword(lib.usernamecreator(), passw)
            print(result)
            if "Password is valid" in result:
                break
        else:
            break

    accounts = []
    cookies = []

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
        username = lib.usernamecreator()
        bar = tqdm(total=100)
        bar.set_description(f"Initial setup completed [{x + 1}/{executionCount}]")
        bar.update(20)
        chrome = Chromium(addr_or_opts=port)
        page = chrome.get_tab(id_or_num=1)
        page.get("https://mail.tm/en")
        page.ele('xpath://*[@id="__nuxt"]/div[1]/div[2]/div/div/div[2]/button[3]').click()
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
            print(f"\nAn error occurred\n{e}\n")
        finally:
            bar.set_description(f"Signup process [{x + 1}/{executionCount}]")
            bar.update(30)
            tab.wait.url_change("https://www.roblox.com/home", timeout=float('inf'))
            try:
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
                        for i in tab.cookies():
                            cookie = {
                                "name": i["name"],
                                "value": i["value"],
                            }
                            cookies.append(cookie)
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
                        for i in tab.cookies():
                            cookie = {
                                "name": i["name"],
                                "value": i["value"],
                            }
                            cookies.append(cookie)
                        tab.set.cookies.clear()
                        tab.clear_cache()
                        chrome.set.cookies.clear()
                        chrome.clear_cache()
                        chrome.quit()
                        accounts.append({"username": username, "password": passw, "email": email, "emailPassword": emailPassword})
                        bar.close()
                        print(
                            "\nFailed to find verification email. You may need to verify it manually. Skipping and continuing...\n"
                        )
            except Exception as e:
                for i in tab.cookies():
                    cookie = {
                        "name": i["name"],
                        "value": i["value"],
                    }
                    cookies.append(cookie)
                print(cookies)
                tab.set.cookies.clear()
                tab.clear_cache()
                chrome.set.cookies.clear()
                chrome.clear_cache()
                chrome.quit()
                accounts.append({"username": username, "password": passw, "email": email, "emailPassword": emailPassword})
                bar.close()
                print(f"\nFailed to find email verification element. You may need to verify the account manually. Skipping and continuing...\n{e}\n")

    with open("accounts.txt", "a") as f:
        for account in accounts:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(
                f"Username: {account['username']}, Password: {account['password']}, Email: {account['email']}, Email Password: {account['emailPassword']} (Created at {timestamp})\n"
            )
    print("\033[1m" "Credentials:")

    try:
        with open("cookies.json", "r") as file:
            existingData = json.load(file)
    except FileNotFoundError:
        existingData = []

    accountsData = []

    for account in accounts:
        accountData = {
            "username": account["username"],
            "password": account["password"],
            "email": account["email"],
            "emailPassword": account["emailPassword"],
            "cookies": []
        }
        for cookie in cookies:
            accountData["cookies"].append({
                "name": cookie["name"],
                "value": cookie["value"]
            })
        accountsData.append(accountData)

    existingData.extend(accountsData)

    with open("cookies.json", "w") as json_file:
        json.dump(existingData, json_file, indent=4)

    for account in accounts:
        print(f"Username: {account['username']}, Password: {account['password']}, Email: {account['email']}, Email Password: {account['emailPassword']}")
    print("\033[0m" "\nCredentials saved to accounts.txt\nCookies are saved to cookies.json file\n\nHave fun playing Roblox!")


if __name__ == "__main__":
    asyncio.run(main())
