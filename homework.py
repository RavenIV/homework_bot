import logging
import time
import os

import requests
import telegram
from dotenv import load_dotenv

import exceptions

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s: %(levelname)s %(message)s',
    filename='main.log',
    filemode='w',
)


def check_tokens():
    """Проверка наличия обязательных переменных окружения."""
    for variable in (
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID
    ):
        if variable is None:
            logging.critical(
                f'Отсутствует обязательная переменная окружения: {variable}. '
                f'Программа принудительно остановлена.'
            )
            raise exceptions.TokensNotFoundError


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    bot.send_message(TELEGRAM_CHAT_ID, message)
    logging.debug(f'Бот отправил сообщение: "{message}"')


def get_api_answer(timestamp):
    """Отправляет запрос к API и возвращает данные в json-формате."""
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=timestamp)
    except Exception as error:
        logging.error(f'Ошибка при запросе к API: {error}.')
    if response.status_code != 200:
        logging.error(f'Сбой в программе. Код ответа при запросе к API: {response.status_code}')
        raise exceptions.RequestError
    return response.json()


def check_response(response):
    """Проверка ответа API."""
    if not isinstance(response, dict):
        logging.error(f'Сбой в программе: ответ API является {type(response)}')
        raise TypeError
    if not response:
        logging.error('Сбой в программе: ответ API ничего не содержит')
        raise exceptions.InvalidResponseError
    if 'homeworks' not in response:
        raise KeyError
    if not isinstance(response['homeworks'], list):
        raise TypeError


def parse_status(homework):
    """Извлекает из данных о домашней работе её статус."""
    homework_name = homework['homework_name']
    verdict = HOMEWORK_VERDICTS[(homework['status'])]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""

    ...

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    ...

    while True:
        try:

            ...

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            ...
        ...


if __name__ == '__main__':
    main()
