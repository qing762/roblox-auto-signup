import random
import platform
import requests
import sys
import uuid
import time
import hmac
import os
import hashlib
from DrissionPage import errors, SessionPage
from zipfile import ZipFile
from pymailtm import MailTm, Account


def getResourcePath(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class UsernameGenerator:
    # SOURCE: https://github.com/mrsobakin/pungen. Kudos to mrsobakin for the original code.
    CONSONANTS = "bcdfghjklmnpqrstvwxyz"

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

        length = random.randrange(self.min_length, self.max_length+1)

        if random.randrange(5) == 0:
            num_length = random.randrange(3) + 1
            if length - num_length < 2:
                num_length = 0

        for j in range(length - num_length):
            if len(username) > 0:
                if username[-1] in self.CONSONANTS:
                    is_consonant = False
                elif username[-1] in self.CONSONANTS:
                    is_consonant = True
            if not is_double:
                if random.randrange(8) == 0 and len(username) < int(length - num_length) - 1:
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
            # return a random vowel based on the weight
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
        versions = list(filter(lambda ver: int(ver.split(".")[0]) <= 136, versions))
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
                    print("This may take a while, please be patient.... Please do not close the program/terminal.")
                    try:
                        url = f"https://github.com/ungoogled-software/ungoogled-chromium-windows/releases/download/{versions[0]}.1/ungoogled-chromium_{versions[0]}.1_windows_x64.zip"
                        r = requests.get(url, stream=True)
                        r.raise_for_status()
                        with open(f"{unGoogledChromium}.zip", "wb") as file:
                            for chunk in r.iter_content(chunk_size=1024):
                                if chunk:
                                    file.write(chunk)
                        print("Download complete. Proceeding to extract the zip file...")
                    except requests.exceptions.RequestException as e:
                        return f"Download failed: {e}"
                    except PermissionError as e:
                        return f"Permission error: {e}. Please check file permissions or run with administrator privileges."
                    except IOError as e:
                        return f"File I/O error: {e}"
                else:
                    print("Zip file already exists. Proceeding to extract...")
                with ZipFile(f"{unGoogledChromium}.zip", 'r') as browserObject:
                    browserObject.extractall(unGoogledChromium)
                print("Extraction complete. Deleting zip file...")
                os.remove(f"{unGoogledChromium}.zip")
                return "Ungoogled Chromium has been downloaded successfully."
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
            versions = list(filter(lambda ver: int(ver.split(".")[0]) <= 136, versions))
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
        while True:
            if nameFormat:
                username = f"{nameFormat}_{counter}"
                counter += 1
            else:
                if scrambled is True:
                    username = self.generateUsername(scrambled=True)
                else:
                    username = self.generateUsername(scrambled=False)

            r = requests.get(
                f"https://auth.roblox.com/v2/usernames/validate?request.username={username}&request.birthday=04%2F15%2F02&request.context=Signup"
            ).json()

            if r["code"] == 0:
                return username
            else:
                continue

    async def checkUpdate(self):
        try:
            resp = requests.get(
                "https://api.github.com/repos/qing762/roblox-auto-signup/releases/latest"
            )
            latestVer = resp.json()["tag_name"]

            if getattr(sys, 'frozen', False):
                import version  # type: ignore
                currentVer = version.__version__
            else:
                with open("version.txt", "r") as file:
                    currentVer = file.read().strip()

            if currentVer < latestVer:
                print(f"Update available: {latestVer} (Current version: {currentVer})\nYou can download the latest version from: https://github.com/qing762/roblox-auto-signup/releases/latest")
                return currentVer
            else:
                print(f"You are running the latest version: {currentVer}")
                return currentVer
        except Exception as e:
            print(f"An error occurred: {e}")
            return currentVer

    async def checkPassword(self, username, password):
        token = requests.post("https://auth.roblox.com/v2/login", headers={"User-Agent": "Mozilla/5.0"}).headers.get("x-csrf-token")
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
        resp = requests.post("https://auth.roblox.com/v2/passwords/validate", json=data, headers=headers).json()
        if resp["code"] == 0:
            return "\nPassword is valid"
        else:
            return f"\nPassword does not meet the requirements: {resp['message']}"

    async def customization(self, tab):
        tab.listen.start('https://avatar.roblox.com/v1/avatar-inventory?pageLimit=50&sortOption=recentAdded')
        tab.get("https://www.roblox.com/my/avatar")
        result = tab.listen.wait(timeout=10)
        content = result.response.body
        assetDict = {}
        for item in content['avatarInventoryItems']:
            if 'itemCategory' in item:
                assetType = item["itemCategory"]["itemSubType"]
                if assetType not in assetDict:
                    assetDict[assetType] = []
                assetDict[assetType].append(item)
        tab.listen.stop()

        selectedAssets = {}
        for assetType, assets in assetDict.items():
            selectedAssets[assetType] = random.choice(assets)

        for assetType, asset in selectedAssets.items():
            for z in tab.ele(".hlist item-cards-stackable").eles("tag:li"):
                if z.ele("tag:a").attr("data-item-name") == asset["itemName"]:
                    z.ele("tag:a").click()
                    break

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
            time.sleep(2)

    def testProxy(self, proxy):
        try:
            response = requests.get("http://www.google.com", proxies={"http": proxy, "https": proxy}, timeout=5)
            return True, response.status_code
        except Exception:
            return False, "Proxy test failed! Please ensure that the proxy is working correctly. Skipping proxy usage..."

    def generateEmail(self, password="Qing762.chy"):
        if not hasattr(self, 'mailtm'):
            self.mailtm = MailTm()
        domainList = self.mailtm._get_domains_list()
        domain = random.choice(domainList)
        username = self.generateUsername().lower()
        address = f"{username}@{domain}"
        while True:
            try:
                emailID = requests.post("https://api.mail.tm/accounts", json={"address": address, "password": password})
                if emailID.status_code == 201 and "id" in emailID.json():
                    break
                else:
                    print(f"Failed to create email with address {address}. Sleeping for 5 seconds then will retry...")
                    time.sleep(5)
                    username = self.generateUsername().lower()
                    address = f"{username}@{domain}"
            except Exception as e:
                print(f"Error creating email: {e}. Sleeping for 5 seconds then will retry...")
                time.sleep(5)
                username = self.generateUsername().lower()
                address = f"{username}@{domain}"
        token = requests.post(
            "https://api.mail.tm/token",
            json={"address": address, "password": password}
        ).json()["token"]
        return address, password, token, emailID

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
                    with open("analytics.txt", "w") as file:
                        file.write("DO NOT CHANGE ANYTHING IN THIS FILE\n")
                        file.write("analytics=1\n")
                        file.write(f"userID={userId}\n")
                    print("Analytics collection enabled.")
                    return True
                elif analytics in ("n", "no"):
                    with open("analytics.txt", "w") as file:
                        file.write("DO NOT CHANGE ANYTHING IN THIS FILE\n")
                        file.write("analytics=0\n")
                    print("Analytics collection disabled.")
                    return False
                else:
                    continue

    def checkAnalytics(self, version):
        with open("analytics.txt", "r") as file:
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

    def sendAnalytics(self, version, userId=None):
        # DO NOT CHANGE THIS KEY, IT IS USED FOR SIGNING THE ANALYTICS DATA
        key = b"Qing762.chy"

        # THIS USERID IS NOT RELATED TO THE USER'S ROBLOX ACCOUNT, IT IS JUST A UNIQUE ID FOR ANALYTICS PURPOSES
        if userId is None:
            userIdValue = None
            try:
                with open("analytics.txt", "r") as file:
                    for line in file:
                        if line.startswith("userID="):
                            userIdValue = line.strip().split("=", 1)[1]
                            break
            except FileNotFoundError:
                userIdValue = str(uuid.uuid4())
            userId = userIdValue or str(uuid.uuid4())

        message = userId.encode()
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
            verb = random.choice(open(getResourcePath('lib/verbs.txt')).read().split()).strip()
            noun = random.choice(open(getResourcePath('lib/nouns.txt')).read().split()).strip()
            adjective = random.choice(open(getResourcePath('lib/adjectives.txt')).read().split()).strip()
            number = random.randint(10, 99)
            username = verb + noun + adjective + str(number)
            return username
        else:
            gen = UsernameGenerator(10, 15)
            return gen.generate()

    def followUser(self, user, tab):
        userIDList = []
        for x in user:
            try:
                userID = requests.post("https://users.roblox.com/v1/usernames/users", json={"usernames": [x]}).json()["data"][0]["id"]
                url = f"https://www.roblox.com/users/{userID}/profile"
                tab.get(url)
                tab.ele("@class=MuiButtonBase-root MuiIconButton-root web-blox-css-tss-abxp79-IconButton-root profile-header-dropdown MuiIconButton-sizeMedium web-blox-css-mui-3cliw1").click()
                tab.ele("@@class=MuiButtonBase-root MuiMenuItem-root web-blox-css-tss-1uppt56-MenuItem-root MuiMenuItem-gutters MuiMenuItem-root web-blox-css-tss-1uppt56-MenuItem-root MuiMenuItem-gutters web-blox-css-mui-1bwf1ry-Typography-body1@@id=follow-button").click()
                time.sleep(0.5)
            except Exception as e:
                print(f"User {x} not found! Error: {e}")
        return userIDList


if __name__ == "__main__":
    print("This is a library file. Please run main.py instead.")
