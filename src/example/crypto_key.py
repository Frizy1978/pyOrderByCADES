# -*- coding: utf-8 -*-
import sys
# sys.path.append(r'/home/lden/pycades_0.1.30636/build')
import pycades
import base64
import re

class SignContent:
    def __init__(self):
        self.CADESCOM_CADES_BES = 1
        self.CAPICOM_CURRENT_USER_STORE = 2
        self.CAPICOM_MY_STORE = "My"
        self.CAPICOM_STORE_OPEN_MAXIMUM_ALLOWED = 2
        self.CAPICOM_CERTIFICATE_FIND_SUBJECT_NAME = 1
        self.CAPICOM_CERTIFICATE_INCLUDE_WHOLE_CHAIN = 1
        self.CADESCOM_BASE64_TO_BINARY = 1

    def get_certificate_by_subject_name(self, certSubjectName):
        oStore = pycades.Store()
        oStore.Open(self.CAPICOM_CURRENT_USER_STORE, self.CAPICOM_MY_STORE, self.CAPICOM_STORE_OPEN_MAXIMUM_ALLOWED)
        oCertificates = oStore.Certificates.Find(self.CAPICOM_CERTIFICATE_FIND_SUBJECT_NAME, certSubjectName)
        if oCertificates.Count == 0:
            print(f"Certificate not found: {certSubjectName}")
            return False
        oCertificate = oCertificates.Item(1)
        oStore.Close()
        return oCertificate

    def get_certificate_by_thumbprint(self, thumbprint):
        oStore = pycades.Store()
        oStore.Open(self.CAPICOM_CURRENT_USER_STORE, self.CAPICOM_MY_STORE, self.CAPICOM_STORE_OPEN_MAXIMUM_ALLOWED)
        oCertificates = oStore.Certificates.Find(pycades.CAPICOM_CERTIFICATE_FIND_SHA1_HASH, thumbprint)
        if oCertificates.Count == 0:
            print(f"Certificate thumbprint not found: {thumbprint}")
            return False
        oCertificate = oCertificates.Item(1)
        oStore.Close()
        return oCertificate

    def sign_create(self, oCertificate, dataToSign):
        oSigner = pycades.Signer()
        oSigner.Options = self.CAPICOM_CERTIFICATE_INCLUDE_WHOLE_CHAIN
        try:
            oSigner.Certificate = oCertificate
        except Exception as err:
            print(f"Failed to get certificate. Error: {err}")
            return False
        oSigner.CheckCertificate = True
        oSignedData = pycades.SignedData()
        oSignedData.ContentEncoding = self.CADESCOM_BASE64_TO_BINARY
        oSignedData.Content = dataToSign
        try:
            sSignedMessage = oSignedData.SignCades(oSigner, self.CADESCOM_CADES_BES, True, pycades.CADESCOM_ENCODE_BASE64)
        except Exception as err:
            print(f"Failed to create signature. Error: {err}")
            return False
        signed_message = sSignedMessage.replace("\r\n", "")
        # print(f"\n Signed content. signed message: {signed_message}")
        return signed_message
