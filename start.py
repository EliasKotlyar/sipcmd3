#!/usr/bin/python3
from application.notification import NotificationCenter
from threading import Event

from sipsimple.account import AccountManager
from sipsimple.application import SIPApplication
from sipsimple.storage import FileStorage
from sipsimple.core import SIPURI, ToHeader
from sipsimple.lookup import DNSLookup, DNSLookupError
from sipsimple.session import Session
from sipsimple.streams.rtp.audio import AudioStream
from sipsimple.threading.green import run_in_green_thread
from sipclient.configuration import config_directory
from time import sleep

class SimpleCallApplication(SIPApplication):
    pin = 0
    def __init__(self, pin):
        SIPApplication.__init__(self)
        self.ended = Event()
        self.callee = None
        self.session = None
        self.pin = pin
        notification_center = NotificationCenter()
        notification_center.add_observer(self)

    def call(self, callee):
        self.callee = callee
        self.start(FileStorage(config_directory))

    @run_in_green_thread
    def _NH_SIPApplicationDidStart(self, notification):
        self.callee = ToHeader(SIPURI.parse(self.callee))
        print(self.callee)
        try:
            routes = DNSLookup().lookup_sip_proxy(self.callee.uri, ['udp']).wait()
        except DNSLookupError as e:
            print('DNS lookup failed: %s' % str(e))
        else:
            account = AccountManager().default_account
            self.session = Session(account)
            self.session.connect(self.callee, routes, [AudioStream()])

    def _NH_SIPSessionGotRingIndication(self, notification):
        print('Ringing!')

    def _NH_SIPSessionDidStart(self, notification):
        audio_stream = notification.data.streams[0]
        print('Audio session established using "%s" codec at %sHz' % (audio_stream.codec, audio_stream.sample_rate))
        path = "./default.wav"
        audio_stream.start_recording(path)
        dtmp = "*#"+str(self.pin)+"*"
        for c in dtmp:
            #audio_stream.send_dtmf(c)
            pass
        sleep(1)
        audio_stream.stop_recording()

        self.stop()


    def _NH_SIPSessionWillEnd(self, notification):
        print("Hang up...")
        self.stop()

    def _NH_SIPSessionDidFail(self, notification):
        print('Failed to connect')
        self.stop()

    def _NH_SIPSessionDidEnd(self, notification):
        print('Session ended')
        self.stop()

    def _NH_SIPApplicationDidEnd(self, notification):
        self.ended.set()

# place an audio call to the specified URI
application = SimpleCallApplication(1000)
target_uri="sip:**620@192.168.0.1"
application.call(target_uri)
#print("Placing call, press Enter to quit the program")
#input()
#if application.session:
#    application.session.end()
application.ended.wait()