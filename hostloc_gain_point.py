import os
import time
import random
import re
import textwrap
import requests

from pyaes import AESModeOfOperationCBC
from requests import Session


def random_generate_user_space_url() -> list:
    url_list = []
    for i in range(12):
        uid = random.randint(10000, 50000)
        url = "https://hostloc.com/space-uid-{}.html".format(str(uid))
        url_list.append(url)
    return url_list


def anti_cc_to_number(secret: str) -> list:
    text = []
    for value in textwrap.wrap(secret, 2):
        text.append(int(value, 16))
    return text


def check_anti_cc() -> dict:
    result_dict = {}
    header = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
    }
    home_page = "https://hostloc.com/forum.php"
    res = requests.get(home_page, headers=header)
    aes_key = re.findall("toNumbers\(\"(.*?)\"\)", res.text)
    cookie_name = re.findall("cookie=\"(.*?)=\"", res.text)

    if len(aes_key) != 0:
        print("偵測到防 CC 機制開啟")
        if len(aes_key) != 3 or len(cookie_name) != 1:
            result_dict["code"] = 0
        else:
            result_dict["code"] = 1
            result_dict["cookie_name"] = cookie_name[0]
            result_dict["a"] = aes_key[0]
            result_dict["b"] = aes_key[1]
            result_dict["c"] = aes_key[2]
    return result_dict


def generate_anti_cc_cookie() -> dict:
    cookie = {}
    anti_cc_status = check_anti_cc()

    if anti_cc_status:
        if anti_cc_status["code"] == 0:
            print("防 CC 驗證過程所需參數不符合需求，頁面可能存在錯誤")
        else:
            print("自動模擬計算嘗試通過防 CC 驗證")
            a = bytes(anti_cc_to_number(anti_cc_status["a"]))
            b = bytes(anti_cc_to_number(anti_cc_status["b"]))
            c = bytes(anti_cc_to_number(anti_cc_status["c"]))
            cbc_mode = AESModeOfOperationCBC(a, b)
            result = cbc_mode.decrypt(c)

            name = anti_cc_status["cookie_name"]
            cookie[name] = result.hex()
    return cookie


def login(username: str, password: str) -> Session:
    header = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36",
        "origin": "https://hostloc.com",
        "referer": "https://hostloc.com/forum.php",
    }
    login_url = "https://hostloc.com/member.php?mod=logging&action=login&loginsubmit=yes&infloat=yes&lssubmit=yes&inajax=1"
    login_data = {
        "fastloginfield": "username",
        "username": username,
        "password": password,
        "quickforward": "yes",
        "handlekey": "ls",
    }

    session = Session()
    session.headers.update(header)
    session.cookies.update(generate_anti_cc_cookie())
    res = session.post(url=login_url, data=login_data)
    res.raise_for_status()
    return session


def check_login_status(session: Session, count: int) -> bool:
    test_url = "https://hostloc.com/home.php?mod=spacecp"
    res = session.get(test_url)
    res.raise_for_status()
    res.encoding = "UTF-8"
    test_title = re.findall("<title>(.*?)<\/title>", res.text)

    if len(test_title) != 0:
        if test_title[0] != "个人资料 -  全球主机交流论坛 -  Powered by Discuz!":
            print("第", count, "個帳戶登入失敗 !")
            return False
        else:
            print("第", count, "個帳戶登入成功 !")
            return True
    else:
        print("無法在使用者設定頁面找到標題，該頁面存在錯誤或被防 CC 機制攔截 !")
        return False


def print_current_point(session: Session):
    test_url = "https://hostloc.com/forum.php"
    res = session.get(test_url)
    res.raise_for_status()
    res.encoding = "UTF-8"
    point = re.findall("积分: (\d+)", res.text)

    if len(point) != 0:
        print("帳戶目前積分 : " + point[0])
    else:
        print("無法取得帳戶積分，可能頁面存在錯誤或者未登入 !")
    time.sleep(5)


def gain_point(session: Session, count: int):
    if check_login_status(session, count):
        print_current_point(session)
        url_list = random_generate_user_space_url()
        for i in range(len(url_list)):
            url = url_list[i]
            try:
                res = session.get(url)
                res.raise_for_status()
                print("第", i + 1, "個使用者空間連結造訪成功")
                time.sleep(5)
            except Exception as ex:
                print("存取連結時發生例外狀況 : " + str(ex))
        print_current_point(session)
    else:
        print("請檢查您的帳戶是否設定正確 !")


def print_my_ip():
    api_url = "https://api.ipify.org/"
    try:
        res = requests.get(url=api_url)
        res.raise_for_status()
        res.encoding = "UTF-8"
        print("目前使用 IP 位址 : " + res.text)
    except Exception as ex:
        print("取得目前 IP 位址失敗 : " + str(ex))


if __name__ == "__main__":
    username = os.environ["HOSTLOC_USERNAME"]
    password = os.environ["HOSTLOC_PASSWORD"]

    username_list = username.split(",")
    password_list = password.split(",")

    if not username or not password:
        print("找不到帳號或密碼，請檢查環境變數是否設定正確 !")
    elif len(username_list) != len(password_list):
        print("帳號與密碼個數不一致，請檢查環境變數設定是否疏漏 !")
    else:
        print_my_ip()
        print("共偵測到", len(username_list), "個帳戶，開始取得積分")
        print("-" * 30)

        for i in range(len(username_list)):
            try:
                client = login(username_list[i], password_list[i])
                gain_point(client, i + 1)
                print("-" * 30)
            except Exception as ex:
                print("程式執行時發生例外狀況 : " + str(ex))
                print("-" * 30)
        print("程式執行完畢，取得積分過程結束")
