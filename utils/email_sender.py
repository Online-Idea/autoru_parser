import logging
from datetime import date
import os
import smtplib
import zipfile
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_email(to, subject, message):
    sender = os.environ['EMAIL_LOGIN']
    password = os.environ['EMAIL_PASSWORD']

    # Сообщение
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = to
    msg['Subject'] = subject
    msg.attach(MIMEText(message, 'plain'))

    # Отправляю письмо
    with smtplib.SMTP_SSL('smtp.yandex.ru', 465) as smtp:
        smtp.login(sender, password)
        smtp.sendmail(sender, to, msg.as_string())


def send_email_to_client(client_email: str, file_paths: list) -> None:
    """
    Отправляет письмо с файлом
    @param client_email: почты получателей, разделены запятой
    @param file_paths: путь к файлам
    """
    # TODO рефакторинг
    # Инфо письма
    sender = os.environ['EMAIL_LOGIN']
    password = os.environ['EMAIL_PASSWORD']
    recipients = [client.strip() for client in client_email.split(',')]
    date_str = date.today().strftime('%d.%m.%Y')
    if len(file_paths) > 1:
        subject = f'Сравнительные таблицы {date_str}'
    else:
        file_name_ext = os.path.basename(file_paths[0])
        subject = os.path.splitext(file_name_ext)[0]
    body = 'Добрый день,\n\n' \
           'В приложении сравнительный анализ конкурентов\n\n' \
           'Это письмо отправлено автоматически. Пожалуйста, не отвечайте на него.\n' \
           'Чтобы отписаться от рассылки напишите нам на: info@ra-online.ru'

    # Сообщение
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = client_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    # Прикрепляю файлы
    for file in file_paths:
        file_name_ext = os.path.basename(file)
        with open(file, 'rb') as f:
            attachment = MIMEApplication(f.read(), _subtype='xlsx')
            attachment.add_header('Content-Disposition', 'attachment', filename=file_name_ext)
            msg.attach(attachment)
    
    # Попытка отправка архива
    # path = 'C:\temp\mail_files'
    # archive_name = 'my_archive.zip'
    # zipf = zipfile.ZipFile(archive_name, 'w', zipfile.ZIP_DEFLATED)
    # for root, dirs, files in os.walk(path):
        # for file in files:
            # zipf.write(os.path.join(root, file))
    # zipf.close()
    # with open(archive_name, 'rb') as f:
        # attachment = MIMEApplication(f.read(), _subtype='.zip')
        # attachment.add_header('Content-Disposition', 'attachment', filename=archive_name)
        # msg.attach(attachment)

    # Отправляю письмо
    with smtplib.SMTP_SSL('smtp.yandex.ru', 465) as smtp:
        smtp.login(sender, password)
        smtp.sendmail(sender, recipients, msg.as_string())

    logging.info('Письмо отправлено')
