# -*- coding: utf-8 -*-
from __future__ import annotations
import configparser
import string
import random
from faker import Faker
import json
import requests
import urllib.parse
import time
import base64
from requests.exceptions import HTTPError
from crypto_key import SignContent

parser = configparser.ConfigParser()
parser.read('buildOrderOms.ini')


class Order:
    def __init__(self):
        self.base_url = None
        self.full_url = None
        self.extension = None
        self.client_token = None
        self.oms_id = None
        self.gtin = None
        self.serviceProviderId = None
        self.serial_number_length = None
        self.quantity = None
        self.template_id = None
        self.header = None
        self.orderId = None
        self.buffer_status = None
        self.codes = []
        self.order_json = {}

    def __str__(self):
        info = f"Full URL:{self.full_url} header:{self.header}  json:{self.order_json}\n"
        return info

    def _get_full_url_api_method(self, baseURL, *res, **params):
        url = baseURL
        for r in res:
            url = '{}/{}'.format(url, r)
        if params:
            url = '{}?{}'.format(url, urllib.parse.urlencode(params))
        return url

    def create_order(self):
        json_string = json.dumps(self.order_json, separators=(',', ':'))
        try:
            response = requests.post(self.full_url, headers=self.header, data=json_string)
            response.raise_for_status()
        except HTTPError as http_err:
            print("HTTP error:{}. JSON error text: {}".format(http_err, response.json()))
            return http_err
        except Exception as err:
            print(f"Error (non HTTP): {err}")
            return err
        else:
            print('Create order success!!! Response =--> {}'.format(response.json()))
            self.orderId = response.json()['orderId']
            print(f"orderId={self.orderId}")
            return response.json()['orderId']

    def get_order_status(self):
        url = self._get_full_url_api_method(self.base_url,
                                            self.extension,
                                            'buffer/status',
                                            omsId=self.oms_id,
                                            orderId=self.orderId,
                                            gtin=self.gtin)
        while True:
            try:
                response = requests.get(url, headers=self.header)
                response.raise_for_status()
            except HTTPError as http_err:
                print(f"HTTP error:{http_err}. JSON error text: {response.json()}")
                break
            except Exception as err:
                print(f"Error (non HTTP): {err}")
                break
            else:
                if response.json()['bufferStatus'] == 'PENDING':
                    print('\rBuffer status > PENDING ... ')
                    print(f"2.2. Buffer in PENDING. Status RESPONSE in JSON: {response.json()}")
                    self.buffer_status = "PENDING"
                    time.sleep(0.2)
                elif response.json()['bufferStatus'] == 'ACTIVE' and int(
                        response.json()['leftInBuffer']) < self.quantity:
                    print('OMS buffer is filling!... ')
                    print(f"2.3. OMS buffer is filling. Response status JSON: {response.json()}")
                    self.buffer_status = "FILLS"
                    time.sleep(0.2)
                elif response.json()['bufferStatus'] == 'ACTIVE' and int(
                        response.json()['leftInBuffer']) == self.quantity:
                    print(
                        '\r\n \033[92m All codes from the order are generated, the buffer is full. \033[00m '.format(self.quantity, response.json()['leftInBuffer']))
                    print(
                        f"2.4. OMS Buffer filled success!!! Count codes in buffer: {response.json()['leftInBuffer']} = {self.quantity} ordered codes")
                    print(f"2.5. OMS Buffer filled Response JSON: {response.json()}")
                    self.buffer_status = "FILLED"
                    break
                elif response.json()['bufferStatus'] == 'REJECTED':
                    print(f"Buffer REJECTED!!!. Status RESPONSE in JSON: {response.json()}")
                    self.buffer_status = "REJECTED"
                    break
                elif response.json()['bufferStatus'] == 'EXHAUSTED':
                    print(f"Buffer EXHAUSTED. Status RESPONSE in JSON: {response.json()}")
                    self.buffer_status = "EXHAUSTED"
                    break
                elif response.json()['bufferStatus'] == 'CLOSED':
                    print(f"Buffer CLOSED. Status RESPONSE in JSON: {response.json()}")
                    self.buffer_status = "CLOSED"
                    break
                elif response.json()['bufferStatus'] == 'DELETED':
                    print(f"Buffer DELETED. Status RESPONSE in JSON: {response.json()}")
                    self.buffer_status = "DELETED"
                    break
        return True

    def get_codes_from_order(self):
        order_last_block_id = 0
        quantity = self.quantity
        url = self._get_full_url_api_method(self.base_url,
                                            self.extension,
                                            'codes',
                                            omsId=self.oms_id,
                                            orderId=self.orderId,
                                            gtin=self.gtin,
                                            quantity=quantity,
                                            lastBlockId=order_last_block_id)
        while True:
            try:
                response = requests.get(url, headers=self.header)
                response.raise_for_status()
            except HTTPError as http_err:
                print(f'HTTP error:{http_err}')
                break
            except Exception as err:
                print(f'Error (non HTTP): {err}')
                break
            else:
                uot_list_codes = response.json()['codes']
                self.codes.extend(uot_list_codes)
                order_last_block_id = response.json()['blockId']
                print(f"3.3. Get codes:[{response.json()['codes']}]")
                print(f"3.4. Get codes. Order last block Id:{response.json()['blockId']}")
                if len(uot_list_codes) < self.quantity:
                    print(f"3.5. Count got codes {uot_list_codes} < {self.quantity} count codes in order")
                    url = self._get_full_url_api_method(self.base_url,
                                                        self.extension,
                                                        'codes',
                                                        omsId=self.oms_id,
                                                        orderId=self.orderId,
                                                        gtin=self.gtin,
                                                        quantity=self.quantity,
                                                        lastBlockId=order_last_block_id)
                    print(f"3.6. For get new part of codes make new URL: {url}")
                print('\033[92m Successful! Все коды из заказа получены \033[00m')
                print(f"3.7. Getting codes from order success complete! All codes got!")
                break


# builder
class OrderBuilder:
    def __init__(self):
        self.order = Order()
        self.sign = SignContent()
        self.thumbprint = parser.get("crypto", "thumbprint") # хэш сертификата подписанта
        print(f"\n self.thumbprint = {self.thumbprint}")

    def _create_serial_numbers(self, number, length):
        # chars = 'abcdefghijklnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'
        chars = string.ascii_letters + string.digits
        count = int(number)  # количество серийных номеров
        leng = int(length)  # длина серийного номера
        serial_nums = []
        while len(serial_nums) < count:
            serial_number = ''
            serial_number = ''.join(random.choice(chars) for i in range(leng))
            if len(serial_nums) > 0 and serial_number not in serial_nums:
                serial_nums.append(serial_number)
            elif len(serial_nums) == 0:
                serial_nums.append(serial_number)
        return serial_nums

    def set_extension(self, product_extension):
        self.order.extension = product_extension

    def set_oms_id(self, omsId = None):
        if omsId is None:
            self.order.oms_id = parser.get(self.order.extension, 'omsId')
        else:
            self.order.oms_id = omsId

    def set_header(self):
        self.order.header = eval(parser.get(self.order.extension, "header"))

    def set_base_url(self):
        self.order.base_url = str(parser.get(self.order.extension, "url"))

    def set_full_url(self):
        url = f"{self.order.base_url}/{self.order.extension}/orders?omsId={self.order.oms_id}"
        self.order.full_url = url

    def set_client_token(self, clientToken = None):
        if clientToken is None:
            self.order.client_token = parser.get(self.order.extension, "clientToken")
        else:
            self.order.client_token = clientToken

    def set_header_token(self):
        self.order.header['clientToken'] = self.order.client_token

    def set_gtin(self, g_tin = None):
        if g_tin is None:
            self.order.order_json['products'][0]['gtin'] = parser.get(self.order.extension, "gtin")
        else:
            self.order.order_json['products'][0]['gtin'] = g_tin

    def get_service_provider_id(self):
        pass
        # en_fake = Faker()
        # Faker.seed(0)
        # self.order.serviceProviderId = en_fake.uuid4()
        # self.order.serviceProviderId = "618888d3-afdf-4343-bbb2-d4c01ed183c7"

    def set_serial_number_length(self, snLength = None):
        if snLength is None:
            self.order.serial_number_length = parser.get(self.order.extension, "serialNumberLength")
        else:
            self.order.serial_number_length = snLength

    def set_template_id(self, templateId = None):
        if templateId is None:
            self.order.order_json["products"][0]["templateId"] = int(parser.get(self.order.extension, "templateId"))
        else:
            self.order.order_json["products"][0]["templateId"] = int(templateId)

    def set_quantity(self, quantity):
        self.order.order_json["products"][0]["quantity"] = int(quantity)

    def set_serial_number_type(self, serial_number_type):
        if serial_number_type == "OPERATOR":
            self.order.order_json["products"][0]["serialNumberType"] = "OPERATOR"
        elif serial_number_type == "SELF_MADE":
            self.order.order_json["products"][0]["serialNumberType"] = "SELF_MADE"
            x = self.order.order_json["products"][0]["quantity"]
            print(f"\nquantity: {x} and self.order.serial_number_length: {self.order.serial_number_length}")

            self.order.order_json["products"][0]["serialNumbers"] = self._create_serial_numbers(self.order.order_json["products"][0]["quantity"], self.order.serial_number_length)
        else:
            self.order.order_json["products"][0]["serialNumberType"] = serial_number_type


    def load_json_data(self):
        self.order.order_json = json.loads(parser.get(self.order.extension, "order_json"))

    def sign_content(self):
            cert = self.sign.get_certificate_by_thumbprint(self.thumbprint) # поиск серта по хэшу
            json_string = json.dumps(self.order.order_json, separators=(',', ':')) # преобразовать json  и убрать пробелы
            cont_64 = base64.b64encode(json_string.encode("UTF-8")) # декодирование в base64
            cont_64 = cont_64.decode("UTF-8")
            self.order.header['X-Signature'] = self.sign.sign_create(cert, cont_64)

class OrderTobacco(OrderBuilder):
    def __init__(self):
        super().__init__()
        self.mrp = 0
        self.factoryId = ''
        self.factoryName = ''
        self.factoryAddress = ''
        self.factoryCountry = ''
        self.productionLineId = ''
        self.productCode = ''
        self.productDescription = ''
        self.poNumber = ''
        self.expectedStartDate = ''

    def get_params_settings(self):
        ru_fake = Faker('ru_RU')
        Faker.seed(0)
        en_fake = Faker('en_US')
        Faker.seed(4)

        #Дописать сеттеры для параметров
        self.mrp = int(parser.get(self.order.extension, "mrp"))
        self.factoryId = en_fake.aba()
        self.factoryName = en_fake.company()
        self.factoryAddress = en_fake.address()
        self.factoryCountry = ru_fake.current_country_code()
        self.productionLineId = en_fake.ein()
        self.productCode = en_fake.invalid_ssn()
        self.productDescription = en_fake.sentence(nb_words=4,
                                                   ext_word_list=['tobacco', 'test', 'flavour', 'smoke', 'incredible',
                                                                  'consummate', 'blue smoke', 'best'])
        # self.productDescription = en_fake.sentence(nb_words=4, ext_word_list=['B010:', 'B5AB', '0@><0B=K9', '2:CA', '@0AAK?G0BK9','=5?@527>945==K9','A87K9 4K<', '>B1>@=K9'])
        self.poNumber = en_fake.pyint()
        self.expectedStartDate = en_fake.date_this_decade(before_today=True).strftime("%Y-%m-%d")

    def set_json_data_tabacco(self):
        self.order.order_json["factoryId"] = self.factoryId
        self.order.order_json["factoryName"] = self.factoryName
        self.order.order_json["factoryAddress"] = self.factoryAddress
        self.order.order_json["factoryCountry"] = self.factoryCountry
        self.order.order_json["productionLineId"] = self.productionLineId
        self.order.order_json["productCode"] = self.productCode
        self.order.order_json["productDescription"] = self.productDescription
        self.order.order_json["poNumber"] = self.poNumber
        self.order.order_json["expectedStartDate"] = self.expectedStartDate
        self.order.order_json["products"][0]["mrp"] = self.mrp


class OrderMilk(OrderBuilder):
    def __init__(self):
        super().__init__()
        self.cisType = ''
        self.exporterTaxpayerId = ''
        self.contactPerson = ''
        self.releaseMethodType = ''
        self.createMethodType = ''
        self.productionOrderId = ''
        self.paymentType = ''

    def set_cis_type(self, cisType = 'UNIT'):
        self.order.order_json["products"][0]["cisType"] = cisType

    def set_release_method_type(self, releaseMethodType = 'PRODUCTION'):
        self.order.order_json["releaseMethodType"] = releaseMethodType

    def set_create_method_type(self, createMethodType = 'SELF_MADE'):
        self.order.order_json["createMethodType"] = createMethodType

    def set_production_order_id(self, productionOrderId = '1234567'):
        self.productionOrderId = productionOrderId

    def set_payment_type(self, paymentType = 2):
        self.order.order_json["paymentType"] = paymentType

    def set_exporter_taxpayer_id(self, TaxpayerId):
        self.exporterTaxpayerId = TaxpayerId

    def set_contact_person(self):
        ru_fake = Faker('ru_RU')
        Faker.seed(0)
        # en_fake = Faker('en_US')
        # Faker.seed(4)
        self.order.order_json["contactPerson"] = ru_fake.name()

    # def set_params_settings(self):
    #     self.set_cis_type()
    #     self.set_release_method_type()
    #     self.set_create_method_type()
    #     self.set_production_order_id()
    #     self.set_payment_type()
    #     self.contact_person()

    # def set_json_milk(self):
    #     +self.order.order_json["contactPerson"] = self.contactPerson
    #     +self.order.order_json["releaseMethodType"] = self.releaseMethodType
    #     +self.order.order_json["createMethodType"] = self.createMethodType
    #     +self.order.order_json["paymentType"] = self.paymentType
    #     +self.order.order_json["products"][0]["cisType"] = self.cisType

# director
class OrderDirector:
    def __init__(self):
        self.builder = None

    def construct_order(self, extension, quantityCodes = 1, serialNumberType = "OPERATOR", templateId = None, g_tin=None):
        if extension == "tobacco":
            self.builder = OrderTobacco()
            #формирование полного URL
            self.builder.set_extension(extension)
            self.builder.set_oms_id()
            self.builder.set_header()
            self.builder.set_base_url()
            self.builder.set_full_url()
            self.builder.set_client_token()
            self.builder.set_header_token()
            #заполнение базового JSON
            self.builder.load_json_data()               # загружка JSON из INI файла
            self.builder.set_serial_number_length()  # snLength = None
            self.builder.set_serial_number_type(serialNumberType)  # serial_number_type="OPERATOR"
            self.builder.set_quantity(quantityCodes)  # quantityCodes
            self.builder.set_template_id(templateId)              #templateId = None
            self.builder.set_gtin(g_tin)                     #g_tin = None
            # заполнение JSON для табака
            self.builder.get_params_settings()          #генерация фековых данных
            self.builder.set_json_data_tabacco()        #запись фейковых данных в  JSON

        if extension == "milk":
            self.builder = OrderMilk()
            # формирование полного URL
            self.builder.set_extension(extension)
            self.builder.set_oms_id()
            self.builder.set_header()
            self.builder.set_base_url()
            self.builder.set_full_url()
            self.builder.set_client_token()
            self.builder.set_header_token()
            # заполнение базового JSON
            self.builder.load_json_data()               # загрузка JSON из INI файла
            self.builder.set_serial_number_length()  # snLength = None
            self.builder.set_quantity(quantityCodes)  # quantityCodes
            self.builder.set_serial_number_type(serialNumberType)       # serial_number_type="OPERATOR"
            self.builder.set_template_id(templateId)              # templateId = None
            self.builder.set_gtin(g_tin)                     # g_tin = None
            # заполнение json заказа ТГ Молоко
            self.builder.set_cis_type()                 # UNIT, BUNDLE, SET
            self.builder.set_release_method_type()      # releaseMethodType = 'PRODUCTION'
            self.builder.set_create_method_type()       # createMethodType = 'SELF_MADE'
            self.builder.set_payment_type()             # paymentType = 2
            self.builder.set_contact_person()           #фейковые данные
            #подписание json и формирование header x-signature
            self.builder.sign_content()
    @property
    def order(self):
        return self.builder.order


if __name__ == "__main__":
    # director = OrderDirector()
    # director.construct_order("tobacco", 3)
    # order = director.order
    # order.create_order()
    # print(order.orderId)
    # print(order)
    # while True:
    #     order.get_order_status()
    #     if order.buffer_status == "REJECTED":
    #         print("Error getting codes from buffer!!!")
    #         break
    #     if order.buffer_status == "FILLED":
    #         order.get_codes_from_order()
    #         break
    #     elif order.buffer_status == "EXHAUSTED" or order.buffer_status == "DELETED":
    #         print("All codes have been received from the buffer!!!")
    #         break

    # director.construct_order("lp", 5)
    # order = director.order
    # print(order)
    #
    # director.construct_order("tires", 5)
    # order = director.order
    # print(order)

    director = OrderDirector()
    # director.construct_order("tobacco", 2)
    # order = director.order
    # order.create_order()
    # print(order.orderId)
    # print(order)
    director.construct_order("milk", 3, "SELF_MADE", g_tin= "1241415235")
    order = director.order
    order.create_order()
    print(order.orderId)
    print(order)




