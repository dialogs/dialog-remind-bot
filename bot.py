from dialog_bot_sdk.bot import DialogBot
import grpc
from collections import defaultdict
from dialog_bot_sdk.entities.media.InteractiveMediaGroup import InteractiveMediaStyle
from dialog_bot_sdk.interactive_media import InteractiveMediaGroup, InteractiveMedia, InteractiveMediaSelect, \
    InteractiveMediaConfirm, InteractiveMediaButton

class Strategy:
    def __init__(self, token, endpoint, async_=True):
        self.bot = None
        self.endpoint = endpoint
        self.token = token
        self.async_ = async_
        
    def start(self, *args, **kwargs):
        self.bot = DialogBot.get_secure_bot(
        self.endpoint,  # bot endpoint (specify different endpoint if you want to connect to your on-premise environment)
        grpc.ssl_channel_credentials(), # SSL credentials (empty by default!)
        self.token,  # bot token
        verbose=False # optional parameter, when it's True bot prints info about the called methods, False by default
        )
        if not self.async_:
            self.bot.messaging.on_message(self.on_msg, self.on_click)
        else:
            self.bot.messaging.on_message_async(self.on_msg, self.on_click)
            self.strategy()
        
    def strategy(self, *args, **kwargs):
        pass
    
    def on_msg(self, *params):
        pass
    
    def on_click(self, *params):
        pass
    
    def buttons(self, peer, title, options):
        return self.bot.messaging.send_message(
            peer, title,
            [InteractiveMediaGroup(
                [InteractiveMedia(
                    option[0],
                    InteractiveMediaButton(
                        *option)
                        )
                for option in options]
            )]
        ).wait()
    
    def select(self, title, values, select_id):
        return InteractiveMedia(
                            select_id,
                             InteractiveMediaSelect(values, title, "choose"),
                            InteractiveMediaStyle.INTERACTIVEMEDIASTYLE_DANGER,
                        )
