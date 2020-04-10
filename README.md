# Remindbot

### Params

Параметры бота можно поменять в config.py:                                                                             
BOT_TOKEN - bot token, полученный от Security Bot,                                              
BOT_ENDPOINT - endpoint,                                                                      
DBNAME - имя базы данных в mongodb, куда бот будет записывать все полученные данные,                               
MONGODBLINK - ссылка для развертывания mongodb(хост+порт, либо Atlas). Здесь можно изменить порт, но также нужно изменить его [в самой mongodb](https://www.digitalocean.com/community/tutorials/how-to-install-mongodb-on-ubuntu-18-04-ru),               
LOGS_FILE - путь к файлу вывода логов

Параметры системы распознавания речи asmsolutions:                                        
APIKEY = ''                                                                  
ADDRESS = 'api.asmsolutions.ru'                                                              
MODEL = 'rus_f15_noswear' #название модели                                               
VAD = 'microphone'                                                       

### Prerequisites

Для запуска и работы бота необходимы python >= 3.6 и mongodb

```
sudo apt update
sudo apt install -y mongodb
```
При этом mongodb должна быть запущена

```
sudo systemctl start mongodb
```
Более подробно о запуске, проверке, остановке mongodb написано [здесь](https://www.digitalocean.com/community/tutorials/how-to-install-mongodb-on-ubuntu-18-04-ru)

### Installing
Для начала нужно установить(если нет), создать и активировать virtualenv для бота:

```
pip3 install virtualenv
virtualenv venv_name
source venv_name/bin/activate
```

Теперь устанавливаем необходимые библиотеки:
```
pip3 install -r requirements.txt
```
### Run bot
```
python3 reminder.py
```
Если ваш virtualenv - ./venv_name, то без активации virtualenv запустить можно так:
```
./venv_name/bin/python3 reminder.py
```
