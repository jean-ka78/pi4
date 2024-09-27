import paho.mqtt.client as mqtt

class MQTTClient:
    def __init__(self, broker, topic, username, password, client_id):
        self.broker = broker
        self.topic = topic
        self.username = username
        self.password = password
        self.client_id = client_id
        self.client = self._connect()

    def _connect(self):
        client = mqtt.Client(self.client_id)
        client.username_pw_set(self.username, self.password)
        client.connect(self.broker, 1883, 60)
        return client

    def publish(self, message):
        try:
            self.client.publish(self.topic, message)
        except Exception as e:
            print(f"MQTT publish failed: {e}")
            self.client.reconnect()

    def disconnect(self):
        self.client.disconnect()
