import asyncio
import warnings
import json
import time
import os
import sys
import re
import pyperclip
import random
from datetime import datetime
from DrissionPage import Chromium, ChromiumOptions, errors
from tqdm import TqdmExperimentalWarning
from tqdm.rich import tqdm
from lib.lib import Main, getResourcePath


warnings.filterwarnings("ignore", category=TqdmExperimentalWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="pkg_resources")


async def main():
    lib = Main()
    co = ChromiumOptions()
    co.auto_port().mute(True)

    print("Checking for updates...")
    version = await lib.checkUpdate()

    lib.promptAnalytics()

    while True:
        browserPath = input(
            "\033[1m"
            "\n(RECOMMENDED) Press enter in order to use the default browser path (If you have Chrome installed)"
            "\033[0m"
            "\nIf you prefer to use other Chromium browser other than Chrome, please enter its executable path here. (e.g: C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe)"
            "\nNote that if captcha bypass is chosen, it will be using Ungoogled Chromium which is already included."
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
                "\nThe password will be used for the account and email.\nIf you prefer to use your own password, do make sure that your password is strong enough.\nThis script has a built in password complexity checker.\nPassword: "
            )
            or "Qing762.chy"
        )
        if passw != "Qing762.chy":
            result = await lib.checkPassword(lib.usernameCreator(), passw)
            print(result)
            if "Password is valid" in result:
                break
        else:
            break

    while True:
        verification = input(
            "\033[1m"
            "\n(RECOMMENDED) Press enter in order to enable email verification"
            "\033[0m"
            "\nIf you prefer to turn off email verification, you will risk to lose the account.It might also applicable for people who does not have email verification element"
            "\nWould you like to enable email verification? [y/n] (Default: Yes): "
        )
        if verification.lower() in ["y", "n", ""]:
            break
        else:
            print("\nPlease enter a valid option.")

    nameFormat = input(
        "\033[1m"
        "\n(RECOMMENDED) Press enter in order to use randomized name prefix"
        "\033[0m"
        "\nIf you prefer to go by your own name prefix, please enter it here.\nIt will go by this example: (If name prefix is 'qing', then the account generated will be named 'qing_0', 'qing_1' and so on)\nName prefix: "
    )

    if nameFormat:
        scrambledUsername = None
    else:
        while True:
            scrambledUsername = input("\nWould you like to use a scrambled username?\nIf no, the script will try to generate a structured username, this might increase generation time. [y/n] (Default: Yes): ")
            if scrambledUsername.lower() in ["y", "n", ""]:
                if scrambledUsername.lower() == "y" or scrambledUsername == "":
                    scrambledUsername = True
                else:
                    scrambledUsername = False
                break
            else:
                print("\nPlease enter a valid option.")

    while True:
        customization = input(
            "\nWould you like to customize the account after the generation process with a randomizer? [y/n] (Default: Yes): "
        )
        if customization.lower() in ["y", "n", ""]:
            break
        else:
            print("\nPlease enter a valid option.")

    followUser = input(
        "\nWould you like to follow any additional accounts after generating this account?\n"
        "If yes, enter the usernames separated by commas (,).\n"
        "Leave blank if none.\n"
        "Usernames: "
    )

    proxyUsage = input(
        "\nWould you like to use proxies?\n"
        "If yes, please enter the proxy IP and port in the format of IP:PORT separated by commas (,). (Example: http://localhost:1080).\n"
        "Leave blank if none.\n"
        "Proxy: "
    )

    captchaBypass = input(
        "\nWould you like to bypass captcha through NopeCHA? (Note that there's only up to 200 free solves per day)"
        "\nYou can get a free API key from https://nopecha.com/manage and paste it here."
        "\nIf yes, please enter the API key for the service."
        "\nLeave blank if none."
        "\nAPI Key: "
    )

    while True:
        incognitoUsage = input(
            "\nWould you like to use incognito mode? Note that if captcha bypass is chosen, it will not be using incognito mode automatically. [y/n] (Default: Yes): "
        )
        if incognitoUsage.lower() in ["y", "n", ""]:
            break
        else:
            print("\nPlease enter a valid option.")

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

    if customization.lower() == "y" or customization == "":
        customization = True
    else:
        customization = False

    if followUser != "":
        following = True
        followUserList = followUser.split(",")
        followUserList = [user.strip() for user in followUserList]
    else:
        following = False

    if verification.lower() == "y" or verification == "":
        verification = True
    else:
        verification = False

    if incognitoUsage.lower() == "y" or incognitoUsage == "" and captchaBypass == "":
        co.incognito()

    if captchaBypass != "":
        co.add_extension(getResourcePath("lib/NopeCHA"))
        co.set_browser_path(getResourcePath("lib/ungoogled-chromium_136.0.7103.113-1.1_windows_x64/chrome.exe"))

    proxyList = [proxy.strip() for proxy in proxyUsage.split(",")]
    usableProxies = []
    for proxy in proxyList:
        if lib.testProxy(proxy)[0] is True:
            usableProxies.append(proxy)
        else:
            print(lib.testProxy(proxy)[1])
    proxyNumber = len(usableProxies)

    for x in range(int(executionCount)):
        captchaPresence = True
        while captchaPresence:
            if proxyUsage != "":
                random.shuffle(usableProxies)
                for proxy in usableProxies:
                    co.set_proxy(proxy)

            if "--no-analytics" not in sys.argv:
                lib.checkAnalytics(version)
            if nameFormat:
                username = lib.usernameCreator(nameFormat, None)
            else:
                if scrambledUsername is True:
                    username = lib.usernameCreator(None, scrambled=True)
                else:
                    username = lib.usernameCreator(None, scrambled=False)
            bar = tqdm(total=100)
            bar.set_description(f"Initial setup completed [{x + 1}/{executionCount}]")
            bar.update(10)

            chrome = Chromium(addr_or_opts=co)
            page = chrome.latest_tab
            page.set.window.max()

            accountCookies = []

            if verification is True:
                email, emailPassword, token, emailID = lib.generateEmail(passw)
                bar.set_description(f"Generated email [{x + 1}/{executionCount}]")
                bar.update(10)

            try:
                if captchaBypass != "":
                    page.get(f"https://nopecha.com/setup#{captchaBypass}")
                page.get("https://www.roblox.com/CreateAccount")
                lang = page.run_js_loaded("return window.navigator.userLanguage || window.navigator.language").split("-")[0]
                try:
                    page.ele('@class=btn-cta-lg cookie-btn btn-primary-md btn-min-width', timeout=3).click()
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
                page.ele("@@id=signup-button@@name=signupSubmit@@class=btn-primary-md signup-submit-button btn-full-width").click()
                bar.set_description(f"Signup submitted [{x + 1}/{executionCount}]")
                bar.update(20)

                try:
                    captcha = page.get_frame('xpath://*[@id="arkose-iframe"]')
                    if captcha and proxyNumber >= 2 and captchaBypass != "":
                        print(f"Captcha detected for account {x + 1}, retrying...")
                        bar.close()
                        chrome.quit()
                        captchaPresence = True
                        continue
                    else:
                        captchaPresence = False
                except errors.ElementNotFoundError:
                    pass

            except Exception as e:
                print(f"\nAn error occurred\n{e}\n")
            if not captchaPresence:
                if lang == "en" and captchaBypass == "":
                    page.wait.url_change("https://www.roblox.com/home", timeout=int("10"))
                elif lang == "en" and captchaBypass != "":
                    page.wait.url_change("https://www.roblox.com/home", timeout=float("inf"))
                else:
                    try:
                        if captchaBypass == "":
                            page.wait.url_change("https://www.roblox.com/home", timeout=int("10"))
                        elif captchaBypass != "":
                            page.wait.url_change("https://www.roblox.com/home", timeout=float("inf"))
                    except errors.TimeoutError:
                        if captchaBypass == "":
                            page.wait.url_change("https://www.roblox.com/home", timeout=int("10"))
                        elif captchaBypass != "":
                            page.wait.url_change(f"https://www.roblox.com/{lang}/home", timeout=float("inf"))
                bar.set_description(f"Signup process [{x + 1}/{executionCount}]")
                bar.update(20)

                if verification is True:
                    try:
                        page.ele(".btn-primary-md btn-primary-md btn-min-width").click()
                        if page.ele("@@class=phone-verification-nonpublic-text text-description font-caption-body"):
                            print("Found phone verification element, skipping email verification.\n")
                            bar.update(20)
                            bar.set_description(f"Skipping email verification [{x + 1}/{executionCount}]")
                        elif page.ele(". form-control input-field verification-upsell-modal-input"):
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

                    except Exception as e:
                        print(f"\nAn error occurred during email verification\n{e}\n")
                        print(f"\nFailed to find email verification element. You may need to verify the account manually. Skipping and continuing...\n{e}\n")
                    finally:
                        bar.set_description(f"Saving cookies and clearing data [{x + 1}/{executionCount}]")
                        for i in page.cookies():
                            cookie = {
                                "name": i["name"],
                                "value": i["value"],
                            }
                            accountCookies.append(cookie)
                        bar.update(5)

                        if customization is True:
                            bar.set_description(f"Customizing account [{x + 1}/{executionCount}]")
                            await lib.customization(page)
                            bar.update(5)
                        else:
                            bar.set_description(f"Skipping customization [{x + 1}/{executionCount}]")
                            bar.update(5)

                        if following is True:
                            bar.set_description(f"Following users [{x + 1}/{executionCount}]")
                            try:
                                userIDs = lib.followUser(followUserList, page)
                            except Exception as e:
                                print(f"An error occurred while following users: {e}")
                            bar.update(5)

                        page.set.cookies.clear()
                        page.clear_cache()
                        chrome.set.cookies.clear()
                        chrome.clear_cache()
                        chrome.quit()
                        accounts.append({"username": username, "password": passw, "email": email, "emailPassword": emailPassword, "cookies": accountCookies})

                        if 'e' in locals():
                            bar.set_description(f"Finished account generation with errors [{x + 1}/{executionCount}]")
                        else:
                            bar.set_description(f"Finished account generation [{x + 1}/{executionCount}]")
                        bar.update(100 - bar.n)
                        bar.close()
                else:
                    for i in page.cookies():
                        cookie = {
                            "name": i["name"],
                            "value": i["value"],
                        }
                        accountCookies.append(cookie)
                    bar.update(10)

                    if customization is True:
                        bar.set_description(f"Customizing account [{x + 1}/{executionCount}]")
                        await lib.customization(page)
                        bar.update(15)
                    else:
                        bar.set_description(f"Skipping customization [{x + 1}/{executionCount}]")
                        bar.update(15)

                    if following is True:
                        bar.set_description(f"Following users [{x + 1}/{executionCount}]")
                        try:
                            userIDs = lib.followUser(followUserList, page)
                        except Exception as e:
                            print(f"An error occurred while following users: {e}")
                        bar.update(10)

                    page.set.cookies.clear()
                    page.clear_cache()
                    chrome.set.cookies.clear()
                    chrome.clear_cache()
                    chrome.quit()
                    email = "N/A"
                    emailPassword = "N/A"
                    accounts.append({"username": username, "password": passw, "email": email, "emailPassword": emailPassword, "cookies": accountCookies})
                    bar.set_description(f"Finished account generation [{x + 1}/{executionCount}]")
                    bar.update(100 - bar.n)
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
            "cookies": account["cookies"]
        }
        accountsData.append(accountData)

    existingData.extend(accountsData)

    with open("cookies.json", "w") as jsonFile:
        json.dump(existingData, jsonFile, indent=4)

    for account in accounts:
        print(f"Username: {account['username']}, Password: {account['password']}, Email: {account['email']}, Email Password: {account['emailPassword']}")
    print("\033[0m" "\nCredentials saved to accounts.txt\nCookies are saved to cookies.json file\n\nHave fun playing Roblox!")

    accountManagerFormat = input(
        "\nWould you like to export the account manager format into your clipboard? [y/n] (Default: No): "
    ) or "n"
    if accountManagerFormat.lower() in ["y", "yes"]:
        accountManagerFormatString = ""

        for account in accountsData:
            roblosecurityCookie = None
            for cookie in account["cookies"]:
                if cookie["name"] == ".ROBLOSECURITY":
                    roblosecurityCookie = cookie["value"]
                    break

            if roblosecurityCookie:
                accountManagerFormatString += f"{roblosecurityCookie}\n"
            else:
                print(f"Warning: No .ROBLOSECURITY cookie found for user {account.get('username', 'unknown')}")

        pyperclip.copy(accountManagerFormatString)
        print("Account manager format (cookies) copied to clipboard!")
        print("Select the 'Cookie(s)' option in Roblox Account Manager and paste it into the input field.")
        print("Do note that you'll have to complete the signup process manually in Roblox Account Manager.\n")
    else:
        print()

    for i in range(5, 0, -1):
        print(f"\rExiting in {i} seconds...", end="", flush=True)
        time.sleep(1)
    print("\r\033[KExiting now...")

if __name__ == "__main__":
    asyncio.run(main())
