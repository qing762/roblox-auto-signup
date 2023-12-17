import random
import time
from datetime import datetime
from requests_html import HTMLSession
from selenium.webdriver.common.by import By
from selenium_stealth import stealth
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.select import Select
from seleniumbase import DriverContext


def usernamecreator():
    with open("nouns.txt", "r") as infile:
        nouns = infile.read().strip(" \n").split("\n")
    with open("blacklist.txt", "r") as inline:
        censored = inline.read().strip(" \n").split("\n")
    while True:
        word2 = random.choice(nouns)
        if word2 in censored:
            continue
        word2 = word2.title()
        username = "{}{}".format(word2, random.randint(1, 99))
        request = HTMLSession()
        r = request.get(
            f"https://auth.roblox.com/v2/usernames/validate?request.username={username}&request.birthday=04%2F15%2F02&request.context=Signup"
        ).json
        if r["code"] == 0:
            return username
        else:
            continue


passw = "Qing762.chy"

with DriverContext(uc=True, headless=False, dark_mode=True) as browser:
    stealth(
        browser,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )
    try:
        browser.get("https://roblox.com/")
        bdaymonthelement = browser.find_element(By.NAME, "birthdayMonth")
        if datetime.now().month == 1:
            Select(bdaymonthelement).select_by_value("Jan")
        elif datetime.now().month == 2:
            Select(bdaymonthelement).select_by_value("Feb")
        elif datetime.now().month == 3:
            Select(bdaymonthelement).select_by_value("Mar")
        elif datetime.now().month == 4:
            Select(bdaymonthelement).select_by_value("Apr")
        elif datetime.now().month == 5:
            Select(bdaymonthelement).select_by_value("May")
        elif datetime.now().month == 6:
            Select(bdaymonthelement).select_by_value("Jun")
        elif datetime.now().month == 7:
            Select(bdaymonthelement).select_by_value("Jul")
        elif datetime.now().month == 8:
            Select(bdaymonthelement).select_by_value("Aug")
        elif datetime.now().month == 9:
            Select(bdaymonthelement).select_by_value("Sep")
        elif datetime.now().month == 10:
            Select(bdaymonthelement).select_by_value("Oct")
        elif datetime.now().month == 11:
            Select(bdaymonthelement).select_by_value("Nov")
        elif datetime.now().month == 12:
            Select(bdaymonthelement).select_by_value("Dec")
        else:
            bdaymonthelement.Select("January")
        bdaydayelement = browser.find_element(By.NAME, "birthdayDay")
        if datetime.now().day <= 31:
            Select(bdaydayelement).select_by_value(str(datetime.now().day))
        else:
            Select(bdaydayelement).select_by_value("1")
        bdayyearelement = browser.find_element(By.NAME, "birthdayYear")
        Select(bdayyearelement).select_by_value(str(datetime.now().year - 19))
        usernameelement = browser.find_element(By.NAME, "signupUsername")
        username = usernamecreator()
        usernameelement.send_keys(username)
        passwordelement = browser.find_element(By.NAME, "signupPassword")
        passwordelement.send_keys(passw)
        time.sleep(2)
        browser.execute_script(
            "arguments[0].click();",
            browser.find_element(By.XPATH, '//*[@id="signup-button"]'),
        )
    except Exception:
        print(f"An error occured\n{Exception}")
    finally:
        element = WebDriverWait(driver=browser, timeout=60).until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="upsell-card-secondary-button"]')
            )
        )
        browser.quit()
        print(f"Your username: {username}\nYour password: {passw}\n")
        print(
            "Note that you will need to verify your email. For safety purposes, change your password as well (if you're are sticking with the default password).\n"
        )
        print("Have fun playing Roblox!")
        exit()
