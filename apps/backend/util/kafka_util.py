
import json
from config.base import settings
from kafka import KafkaProducer


class KafkaProducerAI:
    instance = None

    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            cls.instance = KafkaProducer(bootstrap_servers=settings.KAFKA_CLUSTER,
                                         value_serializer=lambda v: json.dumps(v).encode('ascii'))
        return cls.instance
    
class KafkaProducerBT:
    instance = None

    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            cls.instance = KafkaProducer(bootstrap_servers=settings.KAFKA_CLUSTER_BT,
                                         value_serializer=lambda v: json.dumps(v).encode('ascii'))
        return cls.instance
