import random
import platform
import requests
import sys
import uuid
import hmac
import os
import hashlib
import shutil
import re
import asyncio
import json
from DrissionPage import errors, SessionPage
from zipfile import ZipFile
from datetime import datetime
from pymailtm import MailTm, Account


def getResourcePath(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class UsernameGenerator:
    # SOURCE: https://github.com/mrsobakin/pungen. Kudos to @mrsobakin for the original code.
    CONSONANTS = "bcdfghjklmnpqrstvwxyz"
    VOWELS = "aeiou"

    CONS_WEIGHTED = ("tn", "rshd", "lfcm", "gypwb", "vbjxq", "z")
    VOW_WEIGHTED = ("eao", "iu")
    DOUBLE_CONS = ("he", "re", "ti", "ti", "hi", "to", "ll", "tt", "nn", "pp", "th", "nd", "st", "qu")
    DOUBLE_VOW = ("ee", "oo", "ei", "ou", "ai", "ea", "an", "er", "in", "on", "at", "es", "en", "of", "ed", "or", "as")

    def __init__(self, min_length, max_length=None):
        self.set_length(min_length, max_length)

    def set_length(self, min_length, max_length):
        if not max_length:
            max_length = min_length

        self.min_length = min_length
        self.max_length = max_length

    def generate(self):
        username, is_double, num_length = "", False, 0

        if random.randrange(10) > 0:
            is_consonant = True
        else:
            is_consonant = False

        length = random.randrange(self.min_length, self.max_length + 1)

        if random.randrange(5) == 0:
            num_length = random.randrange(3) + 1
            if length - num_length < 2:
                num_length = 0

        letterLength = max(1, length - num_length)
        for j in range(letterLength):
            if len(username) > 0:
                if username[-1] in self.CONSONANTS:
                    is_consonant = False
                elif username[-1] in self.VOWELS:
                    is_consonant = True
            if not is_double:
                if random.randrange(8) == 0 and len(username) < int(letterLength) - 1:
                    is_double = True
                if is_consonant:
                    username += self._get_consonant(is_double)
                else:
                    username += self._get_vowel(is_double)
                is_consonant = not is_consonant
            else:
                is_double = False
        if random.randrange(2) == 0:
            username = username[:1].upper() + username[1:]
        if num_length > 0:
            for j in range(num_length):
                username += str(random.randrange(10))

        return username

    def _get_consonant(self, is_double):
        if is_double:
            return random.choice(self.DOUBLE_CONS)
        else:
            i = random.randrange(100)
            if i < 40:
                weight = 0
            elif 65 > i >= 40:
                weight = 1
            elif 80 > i >= 65:
                weight = 2
            elif 90 > i >= 80:
                weight = 3
            elif 97 > i >= 90:
                weight = 4
            else:
                return self.CONS_WEIGHTED[5]
            return self.CONS_WEIGHTED[weight][random.randrange(len(self.CONS_WEIGHTED[weight]))]

    def _get_vowel(self, is_double):
        if is_double:
            return random.choice(self.DOUBLE_VOW)
        else:
            i = random.randrange(100)
            if i < 70:
                weight = 0
            else:
                weight = 1
            return self.VOW_WEIGHTED[weight][random.randrange(len(self.VOW_WEIGHTED[weight]))]


class Main():
    def downloadUngoogledChromium(self):
        system = platform.system()
        page = SessionPage()
        versions = []
        if system == "Windows":
            page.get("https://ungoogled-software.github.io/ungoogled-chromium-binaries/releases/windows/64bit/")
            for x in page.eles("@tag()=li"):
                versionText = x.ele("@tag()=a").text
                versions.append(versionText)
        else:
            print(f"{system} OS is not supported for automated installation yet. Please make sure Ungoogled Chromium is installed in order to use NopeCHA.")
            return
        try:
            versions = list(filter(lambda ver: ver and "." in ver and ver.split(".")[0].isdigit() and int(ver.split(".")[0]) <= 136, versions))
        except (ValueError, IndexError):
            versions = []
        if not versions:
            return "No compatible versions found."
        if system == "Windows":
            unGoogledChromium = f"./lib/ungoogled-chromium_{versions[0]}.1_windows_x64"
            if os.path.exists(unGoogledChromium):
                return
        prompt = input("Would you like to install Ungoogled Chromium for NopeCHA to work? [y/n] (Default: Yes): ")
        if prompt.lower() == "y" or prompt == "" or prompt == "yes":
            if system == "Windows":
                if not os.path.exists(f"{unGoogledChromium}.zip"):
                    print(f"Downloading Ungoogled Chromium version {versions[0]} for Windows...")
                    print("This may take a while, please be patient....\nPlease do not close the program/terminal.")
                    try:
                        url = f"https://github.com/ungoogled-software/ungoogled-chromium-windows/releases/download/{versions[0]}.1/ungoogled-chromium_{versions[0]}.1_windows_x64.zip"
                        r = requests.get(url, stream=True)
                        r.raise_for_status()
                        try:
                            with open(f"{unGoogledChromium}.zip", "wb") as file:
                                for chunk in r.iter_content(chunk_size=1024):
                                    if chunk:
                                        file.write(chunk)
                        finally:
                            r.close()
                        print("Download complete. Proceeding to extract the zip file...")
                    except requests.exceptions.RequestException as e:
                        return f"Download failed: {e}"
                    except PermissionError as e:
                        return f"Permission error: {e}. Please check file permissions or run with administrator privileges."
                    except IOError as e:
                        return f"File I/O error: {e}"
                else:
                    print("Zip file already exists. Proceeding to extract...")
                try:
                    tempExtractDir = f"{unGoogledChromium}_temp"

                    with ZipFile(f"{unGoogledChromium}.zip", 'r') as browserObject:
                        browserObject.extractall(tempExtractDir)

                    extractedItems = os.listdir(tempExtractDir)
                    if len(extractedItems) == 1 and os.path.isdir(os.path.join(tempExtractDir, extractedItems[0])):
                        shutil.move(os.path.join(tempExtractDir, extractedItems[0]), unGoogledChromium)
                        os.rmdir(tempExtractDir)
                    else:
                        os.makedirs(unGoogledChromium, exist_ok=True)
                        for item in extractedItems:
                            shutil.move(os.path.join(tempExtractDir, item), os.path.join(unGoogledChromium, item))
                        os.rmdir(tempExtractDir)

                    print("Extraction complete. Deleting zip file...")
                    os.remove(f"{unGoogledChromium}.zip")
                    return "Ungoogled Chromium has been downloaded successfully."
                except Exception as e:
                    try:
                        os.remove(f"{unGoogledChromium}.zip")
                        if 'tempExtractDir' in locals() and os.path.exists(tempExtractDir):
                            shutil.rmtree(tempExtractDir)
                    except Exception:
                        pass
                    return f"Extraction failed: {e}"
        else:
            return "Download cancelled by user."

    def returnUngoogledChromiumPath(self):
        system = platform.system()
        page = SessionPage()
        versions = []
        if system == "Windows":
            page.get("https://ungoogled-software.github.io/ungoogled-chromium-binaries/releases/windows/64bit/")
            for x in page.eles("@tag()=li"):
                versionText = x.ele("@tag()=a").text
                versions.append(versionText)
            try:
                versions = list(filter(lambda ver: ver and "." in ver and ver.split(".")[0].isdigit() and int(ver.split(".")[0]) <= 136, versions))
            except (ValueError, IndexError):
                versions = []
            if not versions:
                print("No compatible versions found.")
                return
            if system == "Windows":
                unGoogledChromium = f"./lib/ungoogled-chromium_{versions[0]}.1_windows_x64"
                return unGoogledChromium
        else:
            return None

    def usernameCreator(self, nameFormat=None, scrambled=False):
        counter = 0
        maxAttempts = 100

        for attempt in range(maxAttempts):
            try:
                if nameFormat:
                    username = f"{nameFormat}_{counter}"
                    counter += 1
                else:
                    if scrambled is True:
                        username = self.generateUsername(scrambled=True)
                    else:
                        username = self.generateUsername(scrambled=False)

                try:
                    r = requests.get(
                        f"https://auth.roblox.com/v2/usernames/validate?request.username={username}&request.birthday=04%2F15%2F02&request.context=Signup",
                        timeout=10
                    ).json()
                except (requests.exceptions.RequestException, ValueError, KeyError) as e:
                    print(f"Error validating username {username}: {e}")
                    continue

                if r.get("code") == 0:
                    return username
                else:
                    if nameFormat and attempt >= maxAttempts - 1:
                        return self.generateUsername(scrambled=True)
                    continue
            except Exception as e:
                print(f"Error validating username: {e}")
                if attempt >= maxAttempts - 1:
                    return self.generateUsername(scrambled=True)
                continue

        return self.generateUsername(scrambled=True)

    async def checkUpdate(self):
        try:
            resp = requests.get(
                "https://api.github.com/repos/qing762/roblox-auto-signup/releases/latest",
                timeout=10
            )
            resp.raise_for_status()
            response_data = resp.json()
            latestVer = response_data.get("tag_name", "unknown")

            if getattr(sys, 'frozen', False):
                try:
                    import version  # type: ignore
                    currentVer = version.__version__
                except ImportError:
                    currentVer = "unknown"
            else:
                try:
                    with open("version.txt", "r", encoding="utf-8") as file:
                        currentVer = file.read().strip()
                except FileNotFoundError:
                    currentVer = "unknown"

            if currentVer != "unknown" and currentVer < latestVer:
                print(f"Update available: {latestVer} (Current version: {currentVer})\nYou can download the latest version from: https://github.com/qing762/roblox-auto-signup/releases/latest")
                return currentVer
            else:
                print(f"You are running the latest version: {currentVer}")
                return currentVer
        except requests.exceptions.Timeout:
            print("Update check timed out. Continuing with current version.")
            return "unknown"
        except requests.exceptions.RequestException as e:
            print(f"Failed to check for updates: {e}")
            return "unknown"
        except Exception as e:
            print(f"An error occurred during update check: {e}")
            return "unknown"

    async def checkPassword(self, username, password):
        try:
            token = requests.post("https://auth.roblox.com/v2/login", headers={"User-Agent": "Mozilla/5.0"}, timeout=10).headers.get("x-csrf-token")
            data = {
                "username": username,
                "password": password
            }
            headers = {
                "accept": "application/json, text/plain, */*",
                "accept-encoding": "gzip, deflate, br, zstd",
                "accept-language": "en-US,en;q=0.6",
                "content-type": "application/json;charset=UTF-8",
                "origin": "https://www.roblox.com",
                "referer": "https://www.roblox.com",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
                "x-csrf-token": token
            }
            try:
                resp = requests.post("https://auth.roblox.com/v2/passwords/validate", json=data, headers=headers, timeout=10).json()
                if resp.get("code") == 0:
                    return "\nPassword is valid"
                else:
                    return f"\nPassword does not meet the requirements: {resp.get('message', 'Unknown error')}"
            except (requests.exceptions.RequestException, ValueError, KeyError) as e:
                return f"\nPassword validation failed: {e}"
        except Exception as e:
            return f"\nPassword validation error: {e}"

    async def customization(self, tab):
        try:
            tab.listen.start('https://avatar.roblox.com/v1/avatar-inventory')
            tab.get("https://www.roblox.com/my/avatar")
            result = tab.listen.wait(timeout=10)
            content = result.response.body
            assetDict = {}
            for item in content.get('avatarInventoryItems', []):
                if 'itemCategory' in item and 'itemSubType' in item['itemCategory']:
                    assetType = item["itemCategory"]["itemSubType"]
                    if assetType not in assetDict:
                        assetDict[assetType] = []
                    assetDict[assetType].append(item)
            tab.listen.stop()

            selectedAssets = {}
            for assetType, assets in assetDict.items():
                selectedAssets[assetType] = random.choice(assets)

            for assetType, asset in selectedAssets.items():
                try:
                    for z in tab.ele(".hlist item-cards-stackable").eles("tag:li"):
                        if z.ele("tag:a").attr("data-item-name") == asset.get("itemName"):
                            z.ele("tag:a").click()
                            break
                except Exception as e:
                    print(f"Warning: Could not click asset {asset.get('itemName', 'unknown')}: {e}")
        except Exception as e:
            print(f"Warning: Avatar customization failed: {e}")
            return

        bodyType = random.choice([i for i in range(0, 101, 5)])
        try:
            tab.run_js_loaded(f'document.getElementById("body type-scale").value = {bodyType};')
            tab.run_js_loaded('document.getElementById("body type-scale").dispatchEvent(new Event("input"));')
        except errors.JavaScriptError:
            tab.run_js_loaded(f'''
                var slider = document.querySelector('input[aria-label="Body Type Scale"]');
                if (slider) {{
                    var muiSlider = slider.closest('.MuiSlider-root');
                    var rect = muiSlider.getBoundingClientRect();
                    var targetValue = {bodyType};
                    var percentage = targetValue / 100;
                    var targetX = rect.left + (rect.width * percentage);
                    var targetY = rect.top + (rect.height / 2);

                    muiSlider.dispatchEvent(new MouseEvent('mousedown', {{
                        bubbles: true,
                        clientX: targetX,
                        clientY: targetY,
                        button: 0
                    }}));

                    var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                    nativeInputValueSetter.call(slider, targetValue);

                    slider.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    slider.dispatchEvent(new Event('change', {{ bubbles: true }}));

                    muiSlider.dispatchEvent(new MouseEvent('mouseup', {{
                        bubbles: true,
                        clientX: targetX,
                        clientY: targetY,
                        button: 0
                    }}));
                }}
            ''')
            await asyncio.sleep(2)

    def testProxy(self, proxy):
        if not proxy or not proxy.strip():
            return False, "Empty proxy provided"

        try:

            proxy = proxy.strip()

            if not proxy.startswith(('http://', 'https://', 'socks4://', 'socks5://')):
                if re.match(r'^\d+\.\d+\.\d+\.\d+:\d+$', proxy):
                    proxy = "http://" + proxy
                else:
                    return False, f"Invalid proxy format: {proxy}. Expected format: protocol://host:port or IP:PORT"

            if any(char in proxy for char in ['&', '|', ';', '$', '`', '(', ')', '<', '>']):
                return False, f"Proxy contains invalid characters: {proxy}"

            response = requests.get("http://www.google.com", proxies={"http": proxy, "https": proxy}, timeout=10)
            if response.status_code == 200:
                return True, f"Proxy {proxy} is working"
            else:
                return False, f"Proxy {proxy} returned status code {response.status_code}"
        except requests.exceptions.Timeout:
            return False, f"Proxy {proxy} timed out"
        except requests.exceptions.ConnectionError:
            return False, f"Proxy {proxy} connection failed"
        except Exception as e:
            return False, f"Proxy {proxy} test failed: {str(e)}"

    async def generateEmail(self, password="Qing762.chy"):
        if not hasattr(self, 'mailtm'):
            self.mailtm = MailTm()

        maxRetries = 3
        for attempt in range(maxRetries):
            try:
                domainList = self.mailtm._get_domains_list()
                if not domainList:
                    raise Exception("No domains available")

                domain = random.choice(domainList)
                username = self.generateUsername().lower()
                address = f"{username}@{domain}"

                emailID = requests.post("https://api.mail.tm/accounts", json={"address": address, "password": password}, timeout=10)
                if emailID.status_code == 201:
                    try:
                        emailID_data = emailID.json()
                        if "id" in emailID_data:
                            token_response = requests.post(
                                "https://api.mail.tm/token",
                                json={"address": address, "password": password},
                                timeout=10
                            )
                            if token_response.status_code == 200:
                                token_data = token_response.json()
                                if "token" in token_data:
                                    return address, password, token_data["token"], emailID
                                else:
                                    raise Exception("Token not found in response")
                            else:
                                raise Exception(f"Token request failed with status {token_response.status_code}")
                    except (ValueError, KeyError) as json_error:
                        raise Exception(f"Invalid JSON response: {json_error}")
                else:
                    if attempt < maxRetries - 1:
                        print(f"Failed to create email with address {address}. Retrying attempt {attempt + 2}/{maxRetries}...")
                        await asyncio.sleep(5)
                    else:
                        raise Exception(f"Failed to create email after {maxRetries} attempts")
            except Exception as e:
                if attempt < maxRetries - 1:
                    print(f"Error creating email: {e}. Retrying attempt {attempt + 2}/{maxRetries}...")
                    await asyncio.sleep(5)
                else:
                    raise Exception(f"Failed to create email after {maxRetries} attempts: {e}")

    def fetchVerification(self, address=None, password=None, emailID=None):
        if not address or not password or not emailID:
            raise ValueError("Address, password, and emailID must be provided.")
        if not hasattr(self, 'mailtm'):
            self.mailtm = MailTm()
        if not hasattr(self, 'account'):
            self.account = Account(emailID, address, password)
        messages = self.account.get_messages()
        return messages

    def promptAnalytics(self):
        if not os.path.exists("analytics.txt"):
            while True:
                analytics = input("\nNo personal data is collected, but anonymous usage statistics help us improve. Allow data collection? [y/n] (Default: Yes): ").strip().lower()
                if analytics in ("y", "yes", ""):
                    userId = str(uuid.uuid4())
                    with open("analytics.txt", "w", encoding="utf-8") as file:
                        file.write("DO NOT CHANGE ANYTHING IN THIS FILE\n")
                        file.write("analytics=1\n")
                        file.write(f"userID={userId}\n")
                    print("Analytics collection enabled.")
                    return True
                elif analytics in ("n", "no"):
                    with open("analytics.txt", "w", encoding="utf-8") as file:
                        file.write("DO NOT CHANGE ANYTHING IN THIS FILE\n")
                        file.write("analytics=0\n")
                    print("Analytics collection disabled.")
                    return False
                else:
                    print("Please enter a valid option (y/n).")

    def checkAnalytics(self, version):
        try:
            with open("analytics.txt", "r", encoding="utf-8") as file:
                lines = file.readlines()
                analytics = None
                userId = None
                for line in lines:
                    if line.startswith("analytics="):
                        analytics = line.strip().split("=", 1)[1]
                    elif line.startswith("userID="):
                        userId = line.strip().split("=", 1)[1]
                if analytics == "1":
                    self.sendAnalytics(version, userId)
                elif analytics == "0":
                    return False
        except FileNotFoundError:
            print("Analytics configuration file not found.")
            return False
        except Exception as e:
            print(f"Error reading analytics configuration: {e}")
            return False

    def sendAnalytics(self, version, userId=None):
        # DO NOT CHANGE THIS KEY, IT IS USED FOR SIGNING THE ANALYTICS DATA
        key = b"Qing762.chy"

        # THIS USERID IS NOT RELATED TO THE USER'S ROBLOX ACCOUNT, IT IS JUST A UNIQUE ID FOR ANALYTICS PURPOSES
        if userId is None:
            userIdValue = None
            try:
                with open("analytics.txt", "r", encoding="utf-8") as file:
                    for line in file:
                        if line.startswith("userID="):
                            userIdValue = line.strip().split("=", 1)[1]
                            break
            except FileNotFoundError:
                userIdValue = str(uuid.uuid4())
            userId = userIdValue or str(uuid.uuid4())

        message = userId.encode('utf-8')
        signature = hmac.new(key, message, hashlib.sha256).hexdigest()

        data = {
            "userId": userId,
            "signature": signature,
            "version": version
        }
        try:
            response = requests.post(
                "https://qing762.is-a.dev/analytics/roblox",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 200:
                pass
            else:
                print(f"\nFailed to send analytics data. Status code: {response.status_code}")
        except requests.RequestException as e:
            print(f"\nAn error occurred while sending analytics data: {e}")

    def generateUsername(self, scrambled=None):
        if scrambled is False:
            try:
                with open(getResourcePath('lib/verbs.txt'), 'r', encoding='utf-8') as f:
                    verbs = f.read().split()
                with open(getResourcePath('lib/nouns.txt'), 'r', encoding='utf-8') as f:
                    nouns = f.read().split()
                with open(getResourcePath('lib/adjectives.txt'), 'r', encoding='utf-8') as f:
                    adjectives = f.read().split()

                if not verbs or not nouns or not adjectives:
                    raise ValueError("One or more word lists are empty")

                verb = random.choice(verbs).strip()
                noun = random.choice(nouns).strip()
                adjective = random.choice(adjectives).strip()
                number = random.randint(10, 99)
                username = verb + noun + adjective + str(number)
                return username
            except FileNotFoundError as e:
                print(f"Warning: Required text files not found: {e}. Falling back to scrambled username.")
                gen = UsernameGenerator(10, 15)
                return gen.generate()
            except Exception as e:
                print(f"Error generating structured username: {e}. Falling back to scrambled username.")
                gen = UsernameGenerator(10, 15)
                return gen.generate()
        else:
            gen = UsernameGenerator(10, 15)
            return gen.generate()

    async def followUser(self, user, tab):
        userIDList = []
        for x in user:
            try:
                response = requests.post("https://users.roblox.com/v1/usernames/users", json={"usernames": [x]}, timeout=10)
                response.raise_for_status()
                data = response.json()

                if not data.get("data") or len(data["data"]) == 0:
                    print(f"User {x} not found!")
                    continue

                userID = data["data"][0]["id"]
                url = f"https://www.roblox.com/users/{userID}/profile"
                tab.get(url)

                await asyncio.sleep(2)

                try:
                    tab.ele("@class=MuiButtonBase-root MuiIconButton-root web-blox-css-tss-abxp79-IconButton-root profile-header-dropdown MuiIconButton-sizeMedium web-blox-css-mui-3cliw1", timeout=5).click()
                    tab.ele("@@class=MuiButtonBase-root MuiMenuItem-root web-blox-css-tss-1uppt56-MenuItem-root MuiMenuItem-gutters MuiMenuItem-root web-blox-css-tss-1uppt56-MenuItem-root MuiMenuItem-gutters web-blox-css-mui-1bwf1ry-Typography-body1@@id=follow-button", timeout=5).click()
                    userIDList.append(userID)
                    print(f"Successfully followed user {x}")
                except errors.ElementNotFoundError:
                    print(f"Could not find follow button for user {x}")
                except Exception as e:
                    print(f"Error clicking follow button for user {x}: {e}")

                await asyncio.sleep(0.5)
            except requests.exceptions.Timeout:
                print(f"Timeout when looking up user {x}")
            except requests.exceptions.RequestException as e:
                print(f"Network error when looking up user {x}: {e}")
            except KeyError as e:
                print(f"User {x} not found or invalid response format: {e}")
            except Exception as e:
                print(f"Unexpected error when following user {x}: {e}")
        return userIDList

    async def saveAccount(self, account):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open("./accounts.txt", "a", encoding="utf-8") as f:
                f.write(
                    f"Username: {account['username']}, Password: {account['password']}, Email: {account['email']}, Email Password: {account['emailPassword']} (Created at {timestamp})\n"
                )
        except Exception as e:
            print(f"Error writing to accounts.txt: {e}")

        try:
            with open("./cookies.json", "r", encoding="utf-8") as file:
                existingData = json.load(file)
        except FileNotFoundError:
            existingData = []
        except Exception as e:
            print(f"Error reading cookies.json: {e}")
            existingData = []

        accountData = {
            "username": account["username"],
            "password": account["password"],
            "email": account["email"],
            "emailPassword": account["emailPassword"],
            "cookies": account["cookies"]
        }
        existingData.append(accountData)

        try:
            with open("./cookies.json", "w", encoding="utf-8") as jsonFile:
                json.dump(existingData, jsonFile, indent=4)
        except Exception as e:
            print(f"Error writing to cookies.json: {e}")


if __name__ == "__main__":
    print("This is a library file. Please run main.py instead.")
