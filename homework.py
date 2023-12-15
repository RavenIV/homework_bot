import logging
import time
import os
import sys

from dotenv import load_dotenv
import requests
import telegram

from exceptions import NotOkStatusResponseError


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


def check_tokens():
    """Проверка наличия обязательных переменных окружения."""
    for variable, name in (
        (PRACTICUM_TOKEN, 'PRACTICUM_TOKEN'),
        (TELEGRAM_TOKEN, 'TELEGRAM_TOKEN'),
        (TELEGRAM_CHAT_ID, 'TELEGRAM_CHAT_ID')
    ):
        if variable is None:
            logging.critical(
                f'Отсутствует обязательная переменная окружения: {name}. '
                f'Программа принудительно остановлена.'
            )
            sys.exit()


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Бот отправил сообщение: "{message}"')
    except telegram.error.TelegramError as error:
        logging.error(f'Ошибка при отправлении сообщения в Telegram: {error}')


def get_api_answer(timestamp):
    """Отправляет запрос к API и возвращает данные в json-формате."""
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params={'from_date': timestamp}
        )
        if response.status_code != 200:
            raise NotOkStatusResponseError('Ошибка при запросе к API', {
                'response': response,
                'status_code': response.status_code
            })
        return response.json()
    except requests.RequestException as error:
        logging.error(f'Ошибка запроса к API: {error}.')


def check_response(response):
    """Проверка ответа API."""
    if not isinstance(response, dict):
        raise TypeError(f'Ответ API ({response}) не приведен к типу словаря.')
    if 'homeworks' not in response:
        raise KeyError('В ответе API нет ключа `homeworks`.')
    if not isinstance(response['homeworks'], list):
        raise TypeError('В ответе API под ключом `homeworks` '
                        'приходят данные не в виде списка')


def parse_status(homework):
    """Извлекает из данных о домашней работе её статус."""
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if homework_name is None or status is None:
        raise KeyError('В ответе API нет ожидаемых ключей')
    elif status not in HOMEWORK_VERDICTS:
        raise KeyError('Неожиданный статус домашней работы в ответе API')
    else:
        return (
            f'Изменился статус проверки работы "{homework_name}". '
            f'{HOMEWORK_VERDICTS[status]}'
        )


def main():
    """Основная логика работы бота."""
    logging.basicConfig(
        level=logging.DEBUG,
        format=(
            '%(asctime)s [%(levelname)s] File "%(pathname)s", '
            'function "%(funcName)s", line %(lineno)d: %(message)s'
        ),
        handlers=[
            logging.StreamHandler(), logging.FileHandler(__file__ + '.log')
        ]
    )

    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    statuses = set()
    message_error = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homeworks = response['homeworks']
            new_statuses = {
                (homework['homework_name'], homework['status'])
                for homework in homeworks
            }
            updates = new_statuses - statuses
            if len(updates) > 0:
                for update in updates:
                    homework_name = update[0]
                    for homework in homeworks:
                        if homework['homework_name'] == homework_name:
                            message = parse_status(homework)
                            send_message(bot, message)
            else:
                logging.debug('В ответе API новые статусы не обнаружены.')
            timestamp = response['current_date']

        except Exception as error:
            new_message_error = f'Сбой в работе программы: {error}'
            logging.error(new_message_error)
            if new_message_error != message_error:
                send_message(bot, new_message_error)
                message_error = new_message_error

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
