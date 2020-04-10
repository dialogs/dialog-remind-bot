from enum import Enum
import logging
from dialog_api import media_and_files_pb2
from dialog_bot_sdk.entities.Peer import Peer, PeerType
from dialog_bot_sdk.entities.UUID import UUID
from pymongo import MongoClient
from config import *
import requests
from datetime import datetime, timedelta
import re

import base64

from bot import *

logger = logging.getLogger('remindbot')
logger.setLevel(logging.DEBUG)
ch = logging.FileHandler(LOGS_FILE)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

class States(Enum):
    START = '0'
    ENTER_EVENT = '1'
    ENTER_TIME = '2'
    ENTER_PERIODICITY = '3'
    
class Tables(Enum):
    STATES = 'states'
    LAST_EVENT = 'last_event'
    EVENTS = 'events'


class PollStrategy(Strategy):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = MongoClient(MONGODBLINK)
        self.db = self.client[DBNAME]
        self.kill = False
        
    def check_code(self, ret):
        if ret.status_code != 200:
            logging.error('error:' + str(ret.status_code) + str(ret.content))
            exit(1)    
        
    def text_from_voice(self, uid, file_id, access_hash):
        try:
            req = media_and_files_pb2.RequestGetFileUrl(
                    file=media_and_files_pb2.FileLocation(file_id=file_id, access_hash=access_hash))
            url = self.bot.internal.media_and_files.GetFileUrl(req).url
            doc = requests.get(url)
            wav_base64 = base64.b64encode(doc.content).decode()
            url = 'http://{}/file'.format(ADDRESS)
            data = {
                'apikey': APIKEY,          # (str or None)
                'model': MODEL,            # (str)
                'wav': wav_base64,         # (bytes)
                'vad_model': VAD,          # (None or str) default: None
                 'async': False,           # (bool) default: False
                'nbest' : 1,
            }
            r = requests.post(url, json=data)
            if r.status_code != 200:
                logging.error('error:' + str(ret.status_code) + str(ret.content))
                return ''
            ret = r.json()
            res = ret[0]
            if res['speech']:
                text = res['speec_info']['text']
                print(text)
                return text
            else:
                print(res)
                return ''
        except Exception as e:
            logger.exception(e)
            return ''
        
    def get_value(self, uid, table):
        val = self.db[table].find_one({'_id': uid})
        if val is None:
            return States.START.value
        return val['value']
        
    def reset_state(self, uid):
        return self.set_value(uid, States.START.value, Tables.STATES.value)
    
    def increment_value(self, uid, value, table):
        self.set_value(uid, str(int(value) + 1), table)
                
    def set_value(self, uid, value, table):
        self.db[table].replace_one({'_id': uid}, {'value': value}, upsert=True)
        return value 
    
    def update_value(self, _id, field, value):
        self.db.events.update_one({"_id": _id}, {"$set": {field: value}})         
    
    def save_event(self, uid, text=None, time=None, periodicity=None):
        '''time: timedelta'''
        is_completed = (time is not None) and (periodicity is not None)
        event = {'uid': uid, 'text': text,'time': None,
                'periodicity': periodicity, 'hours': None,
                 'minutes': None, 'is_completed': is_completed}
        if time is not None:
            for option in ['hours', 'minutes']:
                event[option] = time[option]
        if is_completed:
            (event['time'], tz) = self.make_event_time(uid, time, periodicity)
            self.send_finish_msg(uid, periodicity, text, event['time'], tz)
        last_event = self.db.events.insert_one(event).inserted_id
        self.set_value(uid, last_event, Tables.LAST_EVENT.value)
        
    def update_event(self, uid, mid, time=None, periodicity=None):
            _id = self.get_value(uid, Tables.LAST_EVENT.value)
            msg = self.bot.messaging.get_messages_by_id([UUID.from_api(mid)]).wait()[0]
            if time is not None:
                self.update_value(_id, *time)
            if periodicity is not None:
                self.update_value(_id, 'periodicity', periodicity)
                value = [y for (x, y) in PERIODICITY if x == periodicity][0]
                self.bot.messaging.update_message(msg, msg.message.text_message.text + ' \n '  + value)
            event = self.db.events.find_one({'_id': _id})
            if event['hours'] is not None and event['minutes'] is not None:
                if time is not None:
                    self.bot.messaging.update_message(msg, msg.message.text_message.text + ' \n '  + 
                          '{:02d}:{:02d}'.format(int(event['hours']), int(event['minutes'])))
                if event['periodicity'] is not None:
                    self.on_event_completed(event)
                
    def get_delta_for_periodicity(self, periodicity, event_time):
        if periodicity == 'tomorrow' or (
            periodicity == 'everyday' and event_time <= datetime.utcnow()):
            return timedelta(days=1)
        return timedelta(days=0)
                
    def make_event_time(self, uid, time, periodicity):
        tz = self.get_tz(uid)
        user_day = (datetime.utcnow() + tz).replace(hour=0, minute=0, second=0, microsecond=0)
        time = user_day + timedelta(**time) - tz
        time += self.get_delta_for_periodicity(periodicity, time)
        return (time, tz)   
    
    def send_finish_msg(self, uid, periodicity, text, time, tz):
        if periodicity == 'everyday':
            if time.day != datetime.utcnow().day:
                periodicity = 'tomorrow'
            else:
                periodicity = 'today'
        day = [y for (x, y) in PERIODICITY if periodicity == x][0].lower()
        time += tz
        time = time.strftime("%H:%M")
        self.bot.messaging.send_message(Peer(uid, PeerType.PEERTYPE_PRIVATE),
                                         BOT_ANSWERS['FINISH'].format(day, text, time))
                
    def on_event_completed(self, event):
        uid = event['uid']
        periodicity = event['periodicity']
        _id = self.get_value(uid, Tables.LAST_EVENT.value)
        event = self.db.events.find_one({'_id': _id})
        (time, tz) = self.make_event_time(uid, {key: int(event[key]) for key in ['hours', 'minutes']},
                                   periodicity)
        self.update_value(_id, 'time', time)
        self.update_value(_id, 'is_completed', True)
        self.send_finish_msg(uid, periodicity, event['text'], time, tz)
    
    def send_time_select(self, peer):
         self.bot.messaging.send_message(peer, BOT_ANSWERS[States.ENTER_TIME.name],
                                        [InteractiveMediaGroup(
                    [self.select('Часы', 
                                 {str(x) : str(x) for x in range(0, 24)}, 'hours'),
                    self.select('Минуты', 
                                 {str(x) : str(x) for x in range(0, 60)}, 'minutes')])])
    
    def _handle_start(self, peer):
        uid = peer.id
        state = self.reset_state(uid)
        name = self.bot.users.get_user_by_id(uid).wait().data.name
        self.bot.messaging.send_message(peer, BOT_ANSWERS['START'].format(name))
        self.increment_value(uid, state, Tables.STATES.value) 
        
    def get_tz(self, uid):
        tz = self.bot.users.get_full_profile_by_id(uid).wait().time_zone
        t = datetime.strptime(tz[1:], "%H:%M")
        tdelta = timedelta(hours=t.hour, minutes=t.minute)
        if tz[0] == '-':
            return -tdelta
        return tdelta     
        
    def find_time(self, text):
        time_prep = 'в '
        res = re.compile(r'({})?([0-1]?[0-9]|2[0-3])[:. ][0-5][0-9]'.format(time_prep)).search(text)
        time = None
        if res:
            time = res.group(0)
            text = text.replace(time, '').strip()
            if time_prep in time:
                time = time.replace(time_prep, '')
            if '.' in time:
                time = time.replace('.', ':')
            time = time.replace(' ', ':')
            time = {key: int(value) for (key, value) in zip(['hours', 'minutes'], time.split(':'))}
        return (time, text)
    
    def find_periodicity(self, text):
        for word in STOP_WORDS:
            if text.startswith(word):
                text = text.replace(word + ' ', '', 1)
        for (period_id, period) in PERIODICITY:
            period = period.lower()
            idx = text.find(period)
            if idx != -1:
                periodicity = period_id
                if idx == 0:
                    text = text.replace(period + ' ', '', 1)
                elif idx + len(period) == len(text):
                    text = text[:-len(' ' + period)]
                return (text, periodicity)
        return (text, None)

        
    def _handle_event(self, peer, text):
        periodicity = None
        time = None
        text = text.lower()
        if text[-1] in ['.', '?', '!']:
            text = text[:-1]
        (time, text) = self.find_time(text)
        (text, periodicity) = self.find_periodicity(text)
        text = text.strip()
        self.save_event(peer.id, text, time, periodicity)
        if not time:
            self.send_time_select(peer)
        if not periodicity:
            self.buttons(peer, **BOT_ANSWERS[States.ENTER_PERIODICITY.name])  
    
    def on_msg(self, params):
        try:
            uid = params.peer.id
            peer = params.peer
            if peer.id != params.sender_peer.id:
                return
            text = params.message.text_message.text
            doc_msg = params.message.document_message
            file_id = doc_msg.file_id
            access_hash = doc_msg.access_hash
            if file_id != 0 and access_hash!=0:
                text = self.text_from_voice(uid, file_id, access_hash)
            if text == '/start':
                self._handle_start(peer)
            elif text == '':
                self.bot.messaging.send_message(peer, BOT_ANSWERS['ERROR'])
            else:
                self._handle_event(peer, text)
        except Exception as e:
            logging.exception(e)
            self.kill = True
            raise e
    
    def on_click(self, params):
        try:
            peer = params.peer
            value = params.value
            uid = peer.id
            param_id = params.id
            if param_id in ['hours', 'minutes']:
                time = self.update_event(uid, params.mid, time=[param_id, value])
            if value in [x[0] for x in PERIODICITY]:
                self.update_event(uid, params.mid, periodicity=value)
        except Exception as e:
            logging.exception(e)
            self.kill = True
            raise e
            
    def strategy(self):
        while True:
            if self.kill:
                return
            try:
                now = datetime.utcnow()
                for x in self.db.events.find({'is_completed': True, 'time': {'$lt': now - timedelta(seconds=1),
                                                                         '$gt':now - timedelta(minutes=10)}}):
                    self.bot.messaging.send_message(Peer(x['uid'], PeerType.PEERTYPE_PRIVATE), 
                                                BOT_ANSWERS['REMIND'] + x['text'])
                    if x['periodicity'] == 'everyday':
                        time = x['time'] + timedelta(days=1)
                        self.update_value(x['_id'], 'time', time)
                    else:
                        self.db.events.remove(x)
            except Exception as e:
                logging.exception(e)
                continue
            
            

if __name__ == '__main__':
    while True:
        try:
            logger.info('Start')
            strategy = PollStrategy(token=BOT_TOKEN,
                                           endpoint=BOT_ENDPOINT,async_=True)
            strategy.start()
        except Exception as e:
            logger.exception(e)
            continue
