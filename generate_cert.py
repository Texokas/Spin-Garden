from OpenSSL import crypto
import os

def generate_self_signed_cert():
    # Генерация ключа
    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA, 2048)

    # Создание сертификата
    cert = crypto.X509()
    cert.get_subject().C = "RU"
    cert.get_subject().ST = "Moscow"
    cert.get_subject().L = "Moscow"
    cert.get_subject().O = "Spin Garden"
    cert.get_subject().OU = "Development"
    cert.get_subject().CN = "localhost"
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(365*24*60*60)  # Действителен 1 год
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(k)
    cert.sign(k, 'sha256')

    # Сохранение сертификата
    with open("cert.pem", "wb") as f:
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    
    # Сохранение приватного ключа
    with open("key.pem", "wb") as f:
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))

if __name__ == '__main__':
    generate_self_signed_cert() 