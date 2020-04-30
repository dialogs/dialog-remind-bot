BOT_TOKEN = 'd2ae02c315b4a91016d21e7f8aee5cfc20e5e63b'
BOT_ENDPOINT = 'demo-eem.transmit.im'
DBNAME = 'reminder'
MONGODBLINK = 'mongodb://localhost:27017/'
LOGS_FILE = 'reminder.logs'

#asmsolutions params, replace APIKEY with your APIKEY
APIKEY = ''
ADDRESS = 'api.asmsolutions.ru'
MODEL = 'rus_f15_noswear'
VAD = 'microphone'


#Периодичность напоминаний
PERIODICITY = [('today', 'Сегодня'), ('tomorrow', 'Завтра'), ('everyday', 'Каждый день')]
BOT_ANSWERS = {
    'START' : '{}, добрый день! \n Просто напиши мне, о чем тебе напомнить, и в нужный момент я не дам ничего забыть!',
    'ENTER_TIME' : 'В котором часу напомнить?',
    'ENTER_PERIODICITY': {'title': 'Как часто напоминать?', 'options': PERIODICITY}, 
    'FINISH' : 'Ура, напомню {} про "{}" в {}',
    'REMIND' : 'Напоминание: ',
    'ERROR' : 'Не понял. Повторите, пожалуйста'
              }

STOP_WORDS = ['напомни про', 'напомни о', 'напомнить про', 'напомнить о', 'напомни', 'напомнить']
