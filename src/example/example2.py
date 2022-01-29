# -*- coding: utf-8 -*-
import json
data_json = '{"products":[{"gtin":"04640043460452","quantity":3,"serialNumberType":"OPERATOR","templateId":20,"cisType":"UNIT"}],"contactPerson":"Petrov V.V.","releaseMethodType":"PRODUCTION","createMethodType":"SELF_MADE","paymentType":2}'
json_string = json.loads(data_json,)
print(f"json_string:---> {json_string}")

json_string['products'][0]['gtin'] = 'test'
print(f"json_string changed:---> {json_string}")

