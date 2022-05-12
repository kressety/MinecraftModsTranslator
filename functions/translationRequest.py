from time import sleep

from PyQt6.QtWidgets import QApplication
from requests import post


def authPost(jar, authInfo):
    authHost = 'https://aip.baidubce.com/oauth/2.0/token'
    authData = {
        'grant_type': 'client_credentials',
        'client_id': authInfo['client_id'],
        'client_secret': authInfo['client_secret']
    }
    while True:
        authResponse = post(authHost, authData)
        if authResponse.status_code != 200:
            jar.addStatus('请求失败，请检查网络情况，5秒后重试')
            sleep(5)
            continue
        if 'error' in authResponse.json().keys():
            jar.addStatus('鉴权错误: ' + authResponse.json()['error_description'])
            return False
        return authResponse.json()['access_token']


def translation(jar, word, authToken):
    header = {
        'Content-Type': 'application/json;charset=utf-8'
    }
    params = {
        'from': 'en',
        'to': 'zh',
        'q': word
    }
    transHost = 'https://aip.baidubce.com/rpc/2.0/mt/texttrans/v1?access_token=' + authToken
    while True:
        transResponse = post(transHost, headers=header, params=params)
        if transResponse.status_code != 200:
            jar.addStatus('请求失败，请检查网络情况，5秒后重试')
            sleep(5)
            continue
        if 'error_code' in transResponse.json().keys():
            jar.addStatus('翻译错误: {}: {}'.format(transResponse.json()['error_code'], transResponse.json()['error_msg']))
            return False
        return transResponse.json()['result']['trans_result'][0]


def transJson(jar, js, authToken):
    outputJson = {}
    jar.addStatus('正在翻译，请稍等')
    QApplication.processEvents()
    for key in js:
        outputJson[key] = translation(jar, js[key], authToken)
    jar.addStatus('翻译完成')
    return outputJson
