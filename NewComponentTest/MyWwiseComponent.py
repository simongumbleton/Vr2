
from autobahn.asyncio.component import Component


myWaapiComponent = Component(
    transports = [
                 {
                     u"type": u"websocket",
                     u"url": u"ws://127.0.0.1:8095/waapi",
                     # you can set various websocket options here if you want
                     u"options": {
                         u"open_handshake_timeout": 0,
                         u"auto_ping_timeout":0,
                         u"close_handshake_timeout":0,
                         u"auto_fragment_size":0,

                     }
                 },
             ],
    session_factory=None,
)



# transport_factory.setProtocolOptions(maxFramePayloadSize=0,#1048576,
#                                                  maxMessagePayloadSize=0,#1048576,
#                                                  autoFragmentSize=0,#65536,
#                                                  failByDrop=False,
#                                                  openHandshakeTimeout=0,#2.5,
#                                                  closeHandshakeTimeout=0,#1.,
#                                                  tcpNoDelay=True,
#                                                  autoPingInterval=0,#10.,
#                                                  autoPingTimeout=0,
#                                                  autoPingSize=4,
#                                                  perMessageCompressionOffers=offers,
#                                                  perMessageCompressionAccept=accept)