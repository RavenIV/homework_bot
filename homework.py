import logging
import time
import os

from dotenv import load_dotenv
import requests
import telegram

from exceptions import NotOkStatusResponseError, UnexpectedResponseError

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

TOKEN_NAMES = (
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

VERDICT = ('Изменился статус проверки работы "{name}". {verdict}')
ERROR = 'Сбой в работе программы: {}'
MISSED_TOKENS = 'Отсутствуют переменные окружения: {}.'
MESSAGE_SENT_SUCCESSFULLY = 'Бот отправил сообщение: "{}"'
SEND_MESSAGE_ERROR = 'Ошибка при отправлении в Telegram сообщения: "{}". {}'
REQUEST_PARAMETERS = (
    'Параметры запроса: эндпоинт={0}, headers={1}, params={2}'
)
BAD_REQUEST_ERROR = 'Ошибка запроса к API {error}. ' + REQUEST_PARAMETERS
NOT_OK_STATUS_RESPONSE = ('Запрос к API вернул код ответа "{status}"'
                          + REQUEST_PARAMETERS)
UNEXPECTED_RESPONSE = ('Ответ API вернул ошибку: {name}. '
                       + REQUEST_PARAMETERS)
RESPONSE_NOT_DICT = 'Ответ API не соответствует типу словаря: {}'
HOMEWORKS_NOT_IN_RESPONSE = 'В ответе API нет ключа `homeworks`.'
HOMEWORK_NOT_LIST = ('Тип данных ответа API под ключом `homeworks` '
                     'не является списком: {}')
MISSED_HOMEWORK_KEYS = 'В данных о домашней работе нет ожидаемого ключа {}'
UNEXPERCTED_HOMEWORK_STATUS = 'Неожиданный статус домашней работы: {}'
NO_NEW_STATUSES = 'В ответе API новые статусы не обнаружены.'

logger = logging.getLogger(__name__)


def check_tokens():
    """Проверка наличия обязательных переменных окружения."""
    missed_tokens = [name for name in TOKEN_NAMES if globals()[name] is None]
    if missed_tokens:
        logging.critical(MISSED_TOKENS.format(missed_tokens))
        raise KeyError(MISSED_TOKENS.format(missed_tokens))


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        sent_message = bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(MESSAGE_SENT_SUCCESSFULLY.format(message))
        return sent_message
    except telegram.error.TelegramError as error:
        logging.exception(SEND_MESSAGE_ERROR.format(message, error))


def get_api_answer(timestamp):
    """Отправляет запрос к API и возвращает данные в json-формате."""
    request_parameters = [ENDPOINT, HEADERS, {'from_date': timestamp}]
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params={'from_date': timestamp}
        )
    except requests.RequestException as error:
        raise ConnectionError(
            BAD_REQUEST_ERROR.format(*request_parameters, error=error)
        )
    if response.status_code != 200:
        raise NotOkStatusResponseError(NOT_OK_STATUS_RESPONSE.format(
            *request_parameters, status=response.status_code
        ))
    response = response.json()
    for name in ('code', 'error'):
        if name in response:
            raise UnexpectedResponseError(UNEXPECTED_RESPONSE.format(
                *request_parameters, name=response[name]
            ))
    return response


def check_response(response):
    """Проверка ответа API."""
    if not isinstance(response, dict):
        raise TypeError(RESPONSE_NOT_DICT.format(type(response)))
    if 'homeworks' not in response:
        raise KeyError(HOMEWORKS_NOT_IN_RESPONSE)
    if not isinstance(response['homeworks'], list):
        raise TypeError(HOMEWORK_NOT_LIST.format(type(response["homeworks"])))


def parse_status(homework):
    """Извлекает из данных о домашней работе её статус."""
    for key in ('homework_name', 'status'):
        if key not in homework:
            raise KeyError(MISSED_HOMEWORK_KEYS.format(key))
    status = homework['status']
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(UNEXPERCTED_HOMEWORK_STATUS.format(status))
    return VERDICT.format(
        name=homework['homework_name'], verdict=HOMEWORK_VERDICTS[status]
    )


def main():
    """Основная логика работы бота."""
    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    message_error = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homeworks = response['homeworks']
            if not homeworks:
                logging.debug(NO_NEW_STATUSES)
            else:
                last_homework = homeworks[0]
                sent_message = send_message(bot, parse_status(last_homework))
                if sent_message is not None:
                    timestamp = response.get('current_date', timestamp)
        except Exception as error:
            new_message_error = ERROR.format(error)
            logging.error(new_message_error)
            if new_message_error != message_error:
                sent_message = send_message(bot, new_message_error)
                if sent_message is not None:
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
