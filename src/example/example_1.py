# -*- coding: utf-8 -*-
import json
import requests
import base64
from crypto_key import SignContent
from requests.exceptions import HTTPError

data_json = {"products":[{"gtin":"04640043460452","quantity":3,"serialNumberType":"OPERATOR","templateId":20,"cisType":"UNIT"}],"contactPerson":"Petrov V.V.","releaseMethodType":"PRODUCTION","createMethodType":"SELF_MADE","paymentType":2}
json_string = json.dumps(data_json, separators=(',', ':'))

print(f"\n\n json_string--->{json_string}")
header = {'Content-type': 'application/json', 'Accept': 'application/json', 'clientToken': '7a2fd0d1-5c0c-460a-b12f-52ae4993bcac'}
url_oms = 'https://suz.sandbox.crpt.tech/api/v2/milk/orders?omsId=59d212f4-cd95-4ea6-9eff-95d8e923fbb7'
thumbprint = "4c55734a97a0233b4159e4fbd5c2667033f44cc1" # хэш сертификата подписанта



sign = SignContent()
cert = sign.get_certificate_by_thumbprint(thumbprint)

cont_64 = base64.b64encode(json_string.encode("UTF-8"))
cont_64 = cont_64.decode("UTF-8")
print(f"\n cont_64: {cont_64}")
header['X-Signature'] = sign.sign_create(cert, cont_64)
print(f"\n HEADER: {header}")

try:
    # response = requests.post(url_oms, headers=header, json=json.dumps(json_string, separators=(',', ':')))
    response = requests.post(url_oms, headers=header, data=json_string)
    print("response.json():\n{}\n".format(response.json()))  # JSON Output
    response.raise_for_status()
except HTTPError as http_err:
    print("HTTP error:{}. JSON error text: {}".format(http_err, response.json()))
except Exception as err:
    print(f"Error (non HTTP): {err}")
else:
    print('Create order success!!! Response =--> {}'.format(response.json()))

