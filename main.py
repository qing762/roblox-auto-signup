import asyncio
import warnings
import json
import os
import sys
import re
import pyperclip
import random
import string
import locale
import gc
from datetime import datetime
from DrissionPage import Chromium, ChromiumOptions, errors
from tqdm import TqdmExperimentalWarning
from tqdm.rich import tqdm
from lib.lib import Main, getResourcePath


warnings.filterwarnings("ignore", category=TqdmExperimentalWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="pkg_resources")


def generate_password(length: int = 14) -> str:
    """Generate a random password in the format: letters.numbers

    Example: iascmc.9382
    - letters: 5-8 random lowercase letters
    - numbers: 3-5 random digits
    """
    letter_length = random.randint(5, 8)
    letters = ''.join(random.choice(string.ascii_lowercase) for _ in range(letter_length))

    number_length = random.randint(3, 5)
    numbers = ''.join(random.choice(string.digits) for _ in range(number_length))

    return f"{letters}.{numbers}"


async def main():
    lib = Main()
    co = ChromiumOptions()
    co.auto_port().mute(True)

    print("Checking for updates...")
    version = await lib.checkUpdate()

    lib.promptAnalytics()
    print()
    lib.downloadUngoogledChromium()

    while True:
        try:
            browserPath = lib.returnUngoogledChromiumPath()
        except Exception as e:
            print(f"An error occurred while checking for Ungoogled Chromium: {e}")
            browserPath = None
        if browserPath is None:
            browserPath = input(
                "\033[1m"
                "\n(RECOMMENDED) Press enter in order to use the default browser path (If you have Chrome installed)"
                "\033[0m"
                "\nIf you prefer to use other Chromium browser other than Chrome, please enter its executable path here. (e.g: C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe)"
                "\nNote that if captcha bypass is chosen, it will be using Ungoogled Chromium which is already included."
                "\nHere are some supported browsers that are tested and able to use:"
                "\n- Chrome Browser"
                "\n- Brave Browser"
                "\n- Ungoogled Chromium"
                "\nBrowser executable path: "
            ).replace('"', "").replace("'", "")
            if browserPath != "":

                if any(char in browserPath for char in ['&', '|', ';', '$', '`', '(', ')', '{', '}', '[', ']']):
                    print("Invalid characters detected in browser path. Please enter a valid executable path.")
                elif not browserPath.lower().endswith(('.exe', '.app', '.bin')) and os.name == 'nt':
                    print("Browser path should end with .exe on Windows.")
                elif os.path.exists(browserPath):
                    co.set_browser_path(browserPath)
                    break
                else:
                    print("Please enter a valid path.")
            else:
                break
        else:
            ungoogledChromiumUsage = input(
                "Ungoogled Chromium is detected in the lib folder, would you like to use it? [y/n] (Default: Yes): "
            )
            if ungoogledChromiumUsage.lower() in ["y", "n", ""]:
                if ungoogledChromiumUsage.lower() == "y" or ungoogledChromiumUsage == "":
                    ungoogled_path = lib.returnUngoogledChromiumPath()
                    if ungoogled_path:
                        exe_path = os.path.join(ungoogled_path, 'chrome.exe') if os.name == 'nt' else os.path.join(ungoogled_path, 'chrome')
                        if os.path.exists(exe_path):
                            co.set_browser_path(exe_path)
                        else:
                            print(f"Warning: Ungoogled Chromium executable not found at {exe_path}. Using default browser path.")
                    break
                else:
                    browserPath = input(
                        "\033[1m"
                        "\n(RECOMMENDED) Press enter in order to use the default browser path (If you have Chrome installed)"
                        "\033[0m"
                        "\nIf you prefer to use other Chromium browser other than Chrome, please enter its executable path here. (e.g: C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe)"
                        "\nNote that if captcha bypass is chosen, it will be using Ungoogled Chromium which is already included."
                        "\nHere are some supported browsers that are tested and able to use:"
                        "\n- Chrome Browser"
                        "\n- Brave Browser"
                        "\n- Ungoogled Chromium"
                        "\nBrowser executable path: "
                    ).replace('"', "").replace("'", "")
                    if browserPath != "":

                        if any(char in browserPath for char in ['&', '|', ';', '$', '`', '(', ')', '{', '}', '[', ']']):
                            print("Invalid characters detected in browser path. Please enter a valid executable path.")
                        elif not browserPath.lower().endswith(('.exe', '.app', '.bin')) and os.name == 'nt':
                            print("Browser path should end with .exe on Windows.")
                        elif os.path.exists(browserPath):
                            co.set_browser_path(browserPath)
                            break
                        else:
                            print("Please enter a valid path.")
                    else:
                        break
            else:
                print("\nPlease enter a valid option.")

    # Password selection: random (default), default fixed, or custom with validation
    password_choice = None
    passw = None
    password_use_random = False
    while True:
        password_choice = input(
            "\033[1m"
            "\n(RECOMMENDED) Press enter to use random generated password"
            "\033[0m"
            "\n1. Press enter for random password (Format: randomletters.numbers, e.g., iascmc.9382)"
            "\n2. Type 'default' for default password (Qing762.chy)"
            "\n3. Enter your own custom password"
            "\nPassword choice: "
        ).strip()

        if password_choice == "" or password_choice == "1":
            password_use_random = True
            # We will generate a unique password per account later
            print("Random password mode selected. A unique password will be generated per account.")
            break
        elif password_choice.lower() == "default" or password_choice == "2":
            passw = "Qing762.chy"
            print("Using default password.")
            break
        else:
            # Custom password with Roblox complexity validation
            result = await lib.checkPassword(lib.usernameCreator(), password_choice)
            print(result)
            if "Password is valid" in result:
                passw = password_choice
                break

    while True:
        verification = input(
            "\033[1m"
            "\n(RECOMMENDED) Press enter in order to enable email verification"
            "\033[0m"
            "\nIf you prefer to turn off email verification, you will risk losing the account. It might also be applicable for people who do not have email verification element"
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
        "If yes, enter usernames, numeric user IDs, or profile URLs separated by commas (,).\n"
        "Examples: Builderman, 156, https://www.roblox.com/users/156/profile\n"
        "Leave blank to skip. If a file 'follow.txt' exists, it will be used.\n"
        "Usernames / IDs / URLs: "
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
    ).strip()

    if captchaBypass:

        if not re.match(r'^[a-zA-Z0-9_-]+$', captchaBypass):
            print("Warning: API key contains invalid characters. Only letters, numbers, hyphens and underscores are allowed.")
            captchaBypass = ""
        elif len(captchaBypass) < 10:
            print("Warning: The API key seems too short. Please make sure you entered it correctly.")
            confirm = input("Continue anyway? [y/n]: ")
            if confirm.lower() != "y":
                captchaBypass = ""

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
            if executionCount == "":
                executionCount = 1
                break
            executionCount = int(executionCount)
            if executionCount <= 0:
                print("Please enter a positive number.")
                continue
            if executionCount > 100:
                print("Warning: Generating more than 100 accounts may take a very long time and could trigger rate limits.")
                confirm = input("Are you sure you want to continue? [y/n]: ")
                if confirm.lower() != "y":
                    continue
            break
        except ValueError:
            print("Please enter a valid number.")

    print()

    if customization.lower() == "y" or customization == "":
        customization = True
    else:
        customization = False

    # If input is blank, try to load from follow.txt
    if followUser.strip() == "" and os.path.exists("follow.txt"):
        try:
            with open("follow.txt", "r", encoding="utf-8") as f:
                lines = [ln.strip() for ln in f.readlines()]
                followUser = ",".join([ln for ln in lines if ln])
            print("Loaded follow list from follow.txt")
        except Exception as e:
            print(f"Failed to read follow.txt: {e}")

    if followUser != "":
        following = True
        raw_follow_items = [user.strip() for user in followUser.split(",") if user.strip()]
        followUserList = []
        for item in raw_follow_items:
            # Accept standard usernames
            if re.fullmatch(r'[A-Za-z0-9_]{1,20}', item):
                followUserList.append(item)
                continue
            # Accept numeric user IDs
            if re.fullmatch(r'\d+', item):
                followUserList.append(item)
                continue
            # Accept profile URLs and extract numeric ID
            m = re.match(r'https?://www\.roblox\.com/users/(\d+)/profile', item)
            if m:
                followUserList.append(m.group(1))
                continue
            print(f"Invalid follow entry '{item}'. Use a username, numeric user ID, or a profile URL.")
        # Deduplicate while preserving order
        seen = set()
        followUserList = [x for x in followUserList if not (x in seen or seen.add(x))]
        if not followUserList:
            print("No valid usernames found in follow list.")
            following = False
    else:
        following = False

    if verification.lower() == "y" or verification == "":
        verification = True
    else:
        verification = False

    if (incognitoUsage.lower() == "y" or incognitoUsage == "") and captchaBypass == "":
        co.incognito()

    # Use a dedicated user data folder to avoid conflicts with a running browser instance
    try:
        user_data_dir = os.path.join(os.getcwd(), 'user_data', f'run_{os.getpid()}')
        os.makedirs(user_data_dir, exist_ok=True)
        co.set_user_data_path(user_data_dir)
    except Exception:
        pass

    if captchaBypass != "":
        co.add_extension(getResourcePath("lib/NopeCHA"))
        try:
            ungoogledPath = lib.returnUngoogledChromiumPath()
            if ungoogledPath:
                exe_path = os.path.join(ungoogledPath, 'chrome.exe') if os.name == 'nt' else os.path.join(ungoogledPath, 'chrome')
                if os.path.exists(exe_path):
                    co.set_browser_path(exe_path)
                else:
                    print(f"Warning: Ungoogled Chromium executable not found at {exe_path}, using default browser.")
            else:
                print("Warning: Could not find ungoogled chromium, using default browser")
        except Exception as e:
            print(f"Warning: Could not set ungoogled chromium path: {e}")

    if proxyUsage.strip():
        proxyList = [proxy.strip() for proxy in proxyUsage.split(",") if proxy.strip()]
    else:
        proxyList = []
    usableProxies = []
    for proxy in proxyList:
        if proxy:
            result = lib.testProxy(proxy)
            if result[0] is True:
                usableProxies.append(proxy)
            else:
                print(result[1])
    proxyNumber = len(usableProxies)

    for x in range(int(executionCount)):
        # Determine the password for this account
        current_password = generate_password() if password_use_random else passw
        if password_use_random:
            print(f"Generated password for account {x + 1}: {current_password}")
        captchaPresence = True
        captchaRetries = 0
        maxCaptchaRetries = 5
        while captchaPresence and captchaRetries < maxCaptchaRetries:
            if proxyUsage != "" and usableProxies:
                try:
                    selected_proxy = random.choice(usableProxies)
                    co.set_proxy(selected_proxy)
                    print(f"Using proxy: {selected_proxy}")
                except Exception as e:
                    print(f"Error setting proxy: {e}")

            if "--no-analytics" not in sys.argv:
                lib.checkAnalytics(version)
            if nameFormat:
                username = lib.usernameCreator(nameFormat)
            else:
                if scrambledUsername is True:
                    username = lib.usernameCreator(None, scrambled=True)
                else:
                    username = lib.usernameCreator(None, scrambled=False)
            bar = tqdm(total=100)
            bar.set_description(f"Initial setup completed [{x + 1}/{executionCount}]")
            bar.update(10)

            try:
                chrome = Chromium(addr_or_opts=co)
                page = chrome.latest_tab
                page.set.window.max()
            except Exception as e:
                print(f"Failed to initialize browser: {e}")
                bar.close()
                continue

            accountCookies = []
            email = None
            emailPassword = None

            if verification is True:
                try:
                    email, emailPassword, token, emailID = await lib.generateEmail(current_password)
                    bar.set_description(f"Generated email [{x + 1}/{executionCount}]")
                    bar.update(10)
                except Exception as e:
                    print(f"Failed to generate email: {e}")
                    bar.close()
                    continue

            try:
                if captchaBypass != "":
                    page.get(f"https://nopecha.com/setup#{captchaBypass}")
                page.get("https://www.roblox.com/CreateAccount")
                try:
                    lang_result = page.run_js_loaded("return window.navigator.userLanguage || window.navigator.language")
                    lang = lang_result.split("-")[0] if lang_result and "-" in lang_result else "en"
                except Exception:
                    lang = "en"
                try:
                    page.ele('@class=btn-cta-lg cookie-btn btn-primary-md btn-min-width', timeout=3).click()
                except errors.ElementNotFoundError:
                    pass
                bdaymonthelement = page.ele("#MonthDropdown", timeout=10)

                oldLocale = locale.getlocale(locale.LC_TIME)
                try:
                    locale.setlocale(locale.LC_TIME, 'C')
                    currentMonth = datetime.now().strftime("%b")
                finally:
                    try:
                        locale.setlocale(locale.LC_TIME, oldLocale)
                    except Exception:
                        pass
                bdaymonthelement.select.by_value(currentMonth)
                bdaydayelement = page.ele("#DayDropdown", timeout=10)
                currentDay = datetime.now().day
                try:
                    if currentDay <= 9:
                        bdaydayelement.select.by_value(f"0{currentDay}")
                    else:
                        bdaydayelement.select.by_value(str(currentDay))
                except Exception as e:
                    try:
                        bdaydayelement.select.by_value(str(currentDay))
                    except Exception as e2:
                        print(f"Warning: Could not set day to {currentDay}, using default. Errors: {e}, {e2}")
                currentYear = datetime.now().year - 19
                page.ele("#YearDropdown", timeout=10).select.by_value(str(currentYear))
                page.ele("#signup-username", timeout=10).input(username)
                page.ele("#signup-password", timeout=10).input(current_password)
                await asyncio.sleep(2)
                try:
                    page.ele('@@id=signup-checkbox@@class=checkbox').click()
                except errors.ElementNotFoundError:
                    pass
                await asyncio.sleep(1)
                page.ele("@@id=signup-button@@name=signupSubmit@@class=btn-primary-md signup-submit-button btn-full-width", timeout=10).click()
                bar.set_description(f"Signup submitted [{x + 1}/{executionCount}]")
                bar.update(20)

                try:
                    captcha = page.get_frame('xpath://*[@id="arkose-iframe"]')
                    if captcha and proxyNumber >= 2 and captchaBypass != "":
                        print(f"Captcha detected for account {x + 1}, retrying... (Attempt {captchaRetries + 1}/{maxCaptchaRetries})")
                        bar.close()
                        chrome.quit()
                        captchaPresence = True
                        captchaRetries += 1
                        continue
                    else:
                        captchaPresence = False
                except errors.ElementNotFoundError:
                    captchaPresence = False

            except Exception as e:
                print(f"\nAn error occurred\n{e}\n")
                captchaPresence = False

        if captchaRetries >= maxCaptchaRetries:
            print(f"Max captcha retries reached for account {x + 1}. Skipping this account.")
            try:
                if 'chrome' in locals():
                    chrome.quit()
            except Exception as e:
                print(f"Warning: Could not quit browser: {e}")
                pass
            continue

        if not captchaPresence:
            timeout = 10 if captchaBypass == "" else 300

            try:
                if lang == "en":
                    page.wait.url_change("https://www.roblox.com/home", timeout=timeout)
                else:
                    page.wait.url_change("https://www.roblox.com/home", timeout=timeout)
            except errors.TimeoutError:
                if lang != "en":
                    try:
                        page.wait.url_change(f"https://www.roblox.com/{lang}/home", timeout=timeout)
                    except errors.TimeoutError:
                        pass
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
                            messages = []
                            emailCheckAttempts = 0
                            maxEmailAttempts = 30
                            while emailCheckAttempts < maxEmailAttempts:
                                try:
                                    messages = lib.fetchVerification(email, emailPassword, emailID)
                                    if len(messages) > 0:
                                        break
                                    await asyncio.sleep(5)
                                    emailCheckAttempts += 1
                                except Exception as e:
                                    print(f"Error checking email: {e}")
                                    emailCheckAttempts += 1
                                    await asyncio.sleep(5)

                            if emailCheckAttempts >= maxEmailAttempts:
                                print("Email verification timeout - no email received within expected time")
                                bar.update(10)
                            elif messages and len(messages) > 0:
                                msg = messages[0]
                                body = getattr(msg, 'text', None)
                                if not body and hasattr(msg, 'html') and msg.html and len(msg.html) > 0:
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
                    elif page.ele(".form-control input-field verification-upsell-modal-input"):
                        page.ele(".form-control input-field verification-upsell-modal-input").input(email)
                        page.ele(".modal-button verification-upsell-btn btn-cta-md btn-min-width").click()
                        if page.ele(".verification-upsell-text-body", timeout=60):
                            link = None
                            messages = []
                            emailCheckAttempts = 0
                            maxEmailAttempts = 30
                            while emailCheckAttempts < maxEmailAttempts:
                                try:
                                    messages = lib.fetchVerification(email, emailPassword, emailID)
                                    if len(messages) > 0:
                                        break
                                    await asyncio.sleep(5)
                                    emailCheckAttempts += 1
                                except Exception as e:
                                    print(f"Error checking email: {e}")
                                    emailCheckAttempts += 1
                                    await asyncio.sleep(5)

                            if emailCheckAttempts >= maxEmailAttempts:
                                print("Email verification timeout - no email received within expected time")
                                bar.update(10)
                            elif messages and len(messages) > 0:
                                msg = messages[0]
                                body = getattr(msg, 'text', None)
                                if not body and hasattr(msg, 'html') and msg.html and len(msg.html) > 0:
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
                        follow_error = None
                        try:
                            userIDs = await lib.followUser(followUserList, page)
                        except Exception as e:
                            print(f"An error occurred while following users: {e}")
                            follow_error = e
                        bar.update(5)

                    page.set.cookies.clear()
                    page.clear_cache()
                    chrome.set.cookies.clear()
                    chrome.clear_cache()
                    chrome.quit()
                accounts.append({"username": username, "password": current_password, "email": email, "emailPassword": emailPassword, "cookies": accountCookies})

                if 'follow_error' in locals() and follow_error is not None:
                    bar.set_description(f"Finished account generation with errors [{x + 1}/{executionCount}]")
                else:
                    bar.set_description(f"Finished account generation [{x + 1}/{executionCount}]")

                remaining = max(0, 100 - bar.n)
                if remaining > 0:
                    bar.update(remaining)
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
                        userIDs = await lib.followUser(followUserList, page)
                    except Exception as e:
                        print(f"An error occurred while following users: {e}")
                    bar.update(10)

                page.set.cookies.clear()
                page.clear_cache()
                chrome.set.cookies.clear()
                chrome.clear_cache()
                chrome.quit()
                email = None
                emailPassword = None
                accounts.append({"username": username, "password": current_password, "email": email, "emailPassword": emailPassword, "cookies": accountCookies})
                bar.set_description(f"Finished account generation [{x + 1}/{executionCount}]")

                remaining = max(0, 100 - bar.n)
                if remaining > 0:
                    bar.update(remaining)
                bar.close()

    if not accounts:
        print("No accounts were successfully created.")
        return

    try:
        with open("accounts.txt", "a", encoding="utf-8") as f:
            for account in accounts:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(
                    f"Username: {account['username']}, Password: {account['password']}, Email: {account['email']}, Email Password: {account['emailPassword']} (Created at {timestamp})\n"
                )
    except Exception as e:
        print(f"Error writing to accounts.txt: {e}")

    print("\033[1m" "Credentials:")

    try:
        with open("cookies.json", "r", encoding="utf-8") as file:
            existingData = json.load(file)
    except FileNotFoundError:
        existingData = []
    except Exception as e:
        print(f"Error reading cookies.json: {e}")
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

    try:
        with open("cookies.json", "w", encoding="utf-8") as jsonFile:
            json.dump(existingData, jsonFile, indent=4)
    except Exception as e:
        print(f"Error writing to cookies.json: {e}")

    for account in accounts:
        print(f"Username: {account['username']}, Password: {'*' * len(account['password'])}, Email: {account['email']}, Email Password: {'*' * len(account['emailPassword']) if account['emailPassword'] is not None else 'N/A'}")
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
                print(f"Warning: No .ROBLOSECURITY cookie found for user {account['username']}")

        pyperclip.copy(accountManagerFormatString)
        print("Account manager format (cookies) copied to clipboard!")
        print("Select the 'Cookie(s)' option in Roblox Account Manager and paste it into the input field.")
        print("Do note that you'll have to complete the signup process manually in Roblox Account Manager.\n")
    else:
        print()

    for i in range(5, 0, -1):
        print(f"\rExiting in {i} seconds...", end="", flush=True)
        await asyncio.sleep(1)
    print("\r\033[KExiting now...")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nScript interrupted by user. Cleaning up...")
        try:
            gc.collect()
        except Exception:
            pass
        print("Cleanup complete.")
    except Exception as e:
        print(f"\nUnexpected error occurred: {e}")
        print("Please report this issue at https://qing762.is-a.dev/discord if the error persists.")
