import asyncio
import warnings
import json
import time
import os
import re
from datetime import datetime
from DrissionPage import Chromium, ChromiumOptions, errors
from tqdm import TqdmExperimentalWarning
from tqdm.rich import tqdm
from lib.lib import Main


warnings.filterwarnings("ignore", category=TqdmExperimentalWarning)


async def main():
    lib = Main()
    co = ChromiumOptions()
    co.auto_port().mute(True)

    print("Checking for updates...")
    await lib.checkUpdate()

    while True:
        browserPath = input(
            "\033[1m"
            "\n(RECOMMENDED) Press enter in order to use the default browser path (If you have Chrome installed)"
            "\033[0m"
            "\nIf you prefer to use other Chromium browser other than Chrome, please enter its executable path here. (e.g: C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe)"
            "\nHere are some supported browsers that are tested and able to use:"
            "\n- Chrome Browser"
            "\n- Brave Browser"
            "\nBrowser executable path: "
        ).replace('"', "").replace("'", "")
        if browserPath != "":
            if os.path.exists(browserPath):
                co.set_browser_path(browserPath)
                break
            else:
                print("Please enter a valid path.")
        else:
            break

    while True:
        passw = (
            input(
                "\033[1m"
                "\n(RECOMMENDED) Press enter in order to use the default password"
                "\033[0m"
                "\nThe password will be used for the account and email.\nIf you prefer to use your own password, do make sure that your password is strong enough.\nThis script has a built in password complexity checker.\nPassword: \n"
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

    while True:
        verification = input(
            "\nWould you like to enable email verification? If no you will risk to lose the account. (Hotfix for people who does not have email verification element) [y/n] (Default: Yes): "
        )
        if verification.lower() in ["y", "n", ""]:
            break
        else:
            print("Please enter a valid option.")

    nameFormat = input(
        "\033[1m"
        "\n(RECOMMENDED) Press enter in order to use randomized name prefix"
        "\033[0m"
        "\nIf you prefer to go by your own name prefix, please enter it here.\nIt will go by this example: (If name prefix is 'qing', then the account generated will be named 'qing_0', 'qing_1' and so on)\nName prefix: "
    )

    while True:
        customization = input(
            "\nWould you like to customize the account after the generation process with a randomizer? [y/n] (Default: Yes): "
        )
        if customization.lower() in ["y", "n", ""]:
            break
        else:
            print("Please enter a valid option.")

    proxyUsage = input(
        "\nWould you like to use a proxy?\nPlease enter the proxy IP and port in the format of IP:PORT (Example: http://localhost:1080). Press enter to skip.\nProxy: "
    )

    incognitoUsage = input(
        "\nWould you like to use incognito mode? [y/n] (Default: Yes): "
    )

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

    if customization.lower() == "y" or customization == "":
        customization = True
    else:
        customization = False

    if verification.lower() == "y" or verification == "":
        verification = True
    else:
        verification = False

    if proxyUsage != "":
        if lib.testProxy(proxyUsage)[0] is True:
            co.set_proxy(proxyUsage)
        else:
            print(lib.testProxy(proxyUsage)[1])

    if incognitoUsage.lower() == "y" or incognitoUsage == "":
        co.incognito()

    for x in range(int(executionCount)):
        if nameFormat:
            username = lib.usernamecreator(nameFormat)
        else:
            username = lib.usernamecreator()
        bar = tqdm(total=100)
        bar.set_description(f"Initial setup completed [{x + 1}/{executionCount}]")
        bar.update(10)

        chrome = Chromium(addr_or_opts=co)
        page = chrome.latest_tab
        page.set.window.max()

        if verification is True:
            email, emailPassword, token, emailID = lib.generateEmail(passw)
            bar.set_description(f"Generated email [{x + 1}/{executionCount}]")
            bar.update(10)

        try:
            page.get("https://www.roblox.com/CreateAccount")
            lang = page.run_js_loaded("return window.navigator.userLanguage || window.navigator.language").split("-")[0]
            try:
                page.ele('@@class=btn-cta-lg cookie-btn btn-primary-md btn-min-width@@text()=Accept All', timeout=3).click()
            except errors.ElementNotFoundError:
                pass
            bdaymonthelement = page.ele("#MonthDropdown")
            currentMonth = datetime.now().strftime("%b")
            bdaymonthelement.select.by_value(currentMonth)
            bdaydayelement = page.ele("css:DayDropdown")
            currentDay = datetime.now().day
            if currentDay <= 9:
                bdaydayelement.select.by_value(f"0{currentDay}")
            else:
                bdaydayelement.select.by_value(str(currentDay))
            currentYear = datetime.now().year - 19
            page.ele("#YearDropdown").select.by_value(str(currentYear))
            page.ele("#signup-username").input(username)
            page.ele("#signup-password").input(passw)
            time.sleep(1)
            page.ele("@@id=signup-button@@text()=Sign Up").click()
            bar.set_description(f"Signup submitted [{x + 1}/{executionCount}]")
            bar.update(20)
        except Exception as e:
            print(f"\nAn error occurred\n{e}\n")
        finally:
            if lang == "en":
                page.wait.url_change("https://www.roblox.com/home", timeout=float('inf'))
            else:
                page.wait.url_change(f"https://www.roblox.com/{lang}/home", timeout=float('inf'))
            bar.set_description(f"Signup process [{x + 1}/{executionCount}]")
            bar.update(20)

            if verification is True:
                try:
                    page.ele(".btn-primary-md btn-primary-md btn-min-width").click()
                    page.ele(". form-control input-field verification-upsell-modal-input").input(email)
                    page.ele(".modal-button verification-upsell-btn btn-cta-md btn-min-width").click()
                    if page.ele(".verification-upsell-text-body", timeout=60):
                        link = None
                        while True:
                            messages = lib.fetchVerification(email, emailPassword, emailID)
                            if len(messages) > 0:
                                break
                        msg = messages[0]
                        body = getattr(msg, 'text', None)
                        if not body and hasattr(msg, 'html') and msg.html:
                            body = msg.html[0]
                        if body:
                            match = re.search(r'https://www\.roblox\.com/account/settings/verify-email\?ticket=[^\s)"]+', body)
                            if match:
                                link = match.group(0)
                        if link:
                            bar.set_description(
                                f"Verifying email address [{x + 1}/{executionCount}]"
                            )
                            bar.update(20)
                            page.get(link)
                        else:
                            bar.set_description(f"Email verification link not found [{x + 1}/{executionCount}]")
                            bar.update(10)
                    else:
                        bar.set_description(f"Verification email not found [{x + 1}/{executionCount}]")
                        bar.update(10)

                    bar.set_description(f"Saving cookies and clearing data [{x + 1}/{executionCount}]")
                    for i in page.cookies():
                        cookie = {
                            "name": i["name"],
                            "value": i["value"],
                        }
                        cookies.append(cookie)
                    bar.update(5)

                    if customization is True:
                        bar.set_description(f"Customizing account [{x + 1}/{executionCount}]")
                        await lib.customization(page)
                        bar.update(5)
                    else:
                        bar.set_description(f"Skipping customization [{x + 1}/{executionCount}]")
                        bar.update(5)

                    page.set.cookies.clear()
                    page.clear_cache()
                    chrome.set.cookies.clear()
                    chrome.clear_cache()
                    chrome.quit()
                    accounts.append({"username": username, "password": passw, "email": email, "emailPassword": emailPassword})
                    bar.set_description(f"Finished account generation [{x + 1}/{executionCount}]")
                    bar.update(10)
                    bar.close()
                except Exception as e:
                    print(f"\nAn error occurred during email verification\n{e}\n")
                    for i in page.cookies():
                        cookie = {
                            "name": i["name"],
                            "value": i["value"],
                        }
                        cookies.append(cookie)
                    if customization is True:
                        bar.set_description(f"Attempt to customize account [{x + 1}/{executionCount}]")
                        await lib.customization(page)
                        bar.update(5)
                    page.set.cookies.clear()
                    page.clear_cache()
                    chrome.set.cookies.clear()
                    chrome.clear_cache()
                    chrome.quit()
                    accounts.append({"username": username, "password": passw, "email": email, "emailPassword": emailPassword})
                    bar.set_description(f"Finished account generation with errors [{x + 1}/{executionCount}]")
                    bar.update(10)
                    bar.close()
                    print(f"\nFailed to find email verification element. You may need to verify the account manually. Skipping and continuing...\n{e}\n")
            else:
                for i in page.cookies():
                    cookie = {
                        "name": i["name"],
                        "value": i["value"],
                    }
                    cookies.append(cookie)
                bar.update(10)

                if customization is True:
                    bar.set_description(f"Customizing account [{x + 1}/{executionCount}]")
                    await lib.customization(page)
                    bar.update(20)
                else:
                    bar.set_description(f"Skipping customization [{x + 1}/{executionCount}]")
                    bar.update(20)

                page.set.cookies.clear()
                page.clear_cache()
                chrome.set.cookies.clear()
                chrome.clear_cache()
                chrome.quit()
                email = "N/A"
                emailPassword = "N/A"
                accounts.append({"username": username, "password": passw, "email": email, "emailPassword": emailPassword})
                bar.set_description(f"Finished account generation [{x + 1}/{executionCount}]")
                bar.update(20)
                bar.close()

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
