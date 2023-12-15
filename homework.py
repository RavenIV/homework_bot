import logging
import time
import os

from dotenv import load_dotenv
import requests
import telegram

from exceptions import (
    TokenNotFoundError,
    NotOkStatusResponseError,
    BadRequestError,
    UnexpectedResponseError
)


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

TOKEN_VARIABLE_NAMES = (
    'PRACTICUM_TOKEN',
    'TELEGRAM_TOKEN',
    'TELEGRAM_CHAT_ID'
)

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

VERDICT_MESSAGE = (
    'Изменился статус проверки работы "{name}". {verdict}'
)
ERROR_MESSAGE = 'Сбой в работе программы: {error}'

logger = logging.getLogger(__name__)


def check_tokens():
    """Проверка наличия обязательных переменных окружения."""
    tokens_unavailable = []
    for name in TOKEN_VARIABLE_NAMES:
        if globals()[name] is None:
            tokens_unavailable.append(name)
    if len(tokens_unavailable) != 0:
        logging.critical(
            f'Отсутствуют переменные окружения: {tokens_unavailable}.'
        )
        raise TokenNotFoundError


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Бот отправил сообщение: "{message}"')
    except telegram.error.TelegramError:
        logging.exception(
            f'Ошибка при отправлении в Telegram сообщения: "{message}"'
        )


def get_api_answer(timestamp):
    """Отправляет запрос к API и возвращает данные в json-формате."""
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.RequestException:
        raise BadRequestError(f'Ошибка запроса к API: эндпоинт={ENDPOINT}, '
                              f'headers={HEADERS}, params={params}')
    else:
        if response.status_code != 200:
            raise NotOkStatusResponseError(
                f'Запрос к API (эндпоинт={ENDPOINT}, '
                f'headers={HEADERS}, params={params}). '
                f'вернул код ответа: {response.status_code}'
            )
        response = response.json()
        for name in ('code', 'error'):
            if name in response:
                raise UnexpectedResponseError(
                    f'Ответ API: ошибка={response[name]}. '
                    f'Параметры запроса: эндпоинт={ENDPOINT}, '
                    f'headers={HEADERS}, params={params}'
                )
        return response


def check_response(response):
    """Проверка ответа API."""
    if not isinstance(response, dict):
        raise TypeError(
            f'Ответ API не соответствует типу словаря: {type(response)}'
        )
    if 'homeworks' not in response:
        raise KeyError('В ответе API нет ключа `homeworks`.')
    if not isinstance(response['homeworks'], list):
        raise TypeError(f'Тип данных ответа API под ключом `homeworks` '
                        f'не является списком: {type(response["homeworks"])}')


def parse_status(homework):
    """Извлекает из данных о домашней работе её статус."""
    for key in ('homework_name', 'status'):
        if key not in homework:
            raise KeyError(
                f'В данных о домашней работе нет ожидаемого ключа {key}'
            )
    homework_name = homework['homework_name']
    status = homework['status']
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Неожиданный статус домашней работы: {status}')
    return VERDICT_MESSAGE.format(
        name=homework_name, verdict=HOMEWORK_VERDICTS[status]
    )


def main():
    """Основная логика работы бота."""
    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    homework = {}
    message_error = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = response.get('current_date', timestamp)
            check_response(response)
            homeworks = response['homeworks']
            if len(homeworks) > 0:
                last_homework = homeworks[0]
                if set(last_homework.items()) != set(homework.items()):
                    message = parse_status(last_homework)
                    send_message(bot, message)
                    homework = last_homework
            else:
                logging.debug('В ответе API новые статусы не обнаружены.')
        except Exception as error:
            new_message_error = ERROR_MESSAGE.format(error=error)
            logging.error(new_message_error)
            if new_message_error != message_error:
                try:
                    send_message(bot, new_message_error)
                except telegram.error.TelegramError:
                    logging.exception(
                        f'Не удалось отправить сообщение "{new_message_error}"'
                    )
                else:
                    message_error = new_message_error

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
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
    main()
