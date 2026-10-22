"""Push-to-talk capture. Microphone exists only between press and release."""
import array
import asyncio
import io
import math
import wave
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtMultimedia import QAudioSource, QAudioFormat, QMediaDevices

class Microphone(QObject):
    level=Signal(float)
    finished=Signal(bytes)
    failed=Signal(str)
    def __init__(self,parent=None):
        super().__init__(parent)
        self.source=None
        self.data=bytearray()
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.timeout.connect(self.stop)

    def start(self):
        if self.source:return
        device=QMediaDevices.defaultAudioInput()
        if device.isNull():raise ValueError('No microphone found. Connect one and allow microphone access in system settings.')
        fmt=QAudioFormat();fmt.setSampleRate(16000);fmt.setChannelCount(1);fmt.setSampleFormat(QAudioFormat.Int16)
        if not device.isFormatSupported(fmt):fmt=device.preferredFormat()
        if fmt.sampleFormat() not in (QAudioFormat.Int16,QAudioFormat.Int32,QAudioFormat.Float,QAudioFormat.UInt8):raise ValueError('This microphone format is unsupported. Choose a standard system input device.')
        self.fmt=fmt;self.data=bytearray();self.source=QAudioSource(device,fmt,self)
        self.device=self.source.start()
        if self.device is None:
            self.source.deleteLater();self.source=None
            raise ValueError('Microphone could not start. Allow microphone access and check whether another app is using it.')
        self.device.readyRead.connect(self.read)
        self.source.stateChanged.connect(self.source_state)
        self.timer.start(30000)

    def source_state(self,_):
        if self.source and self.source.error().value:
            self.stop(cancel=True)
            self.failed.emit('Microphone stopped unexpectedly. Check input-device permissions and reconnect the device.')

    def samples(self,data):
        fmt=self.fmt.sampleFormat()
        code={QAudioFormat.Int16:'h',QAudioFormat.Int32:'i',QAudioFormat.Float:'f',QAudioFormat.UInt8:'B'}[fmt]
        values=array.array(code)
        size=values.itemsize
        values.frombytes(bytes(data[:len(data)//size*size]))
        scale={QAudioFormat.Int16:32768,QAudioFormat.Int32:2147483648,QAudioFormat.Float:1,QAudioFormat.UInt8:128}[fmt]
        return [(x-128)/128 if fmt==QAudioFormat.UInt8 else x/scale for x in values]

    def read(self):
        if not self.source:return
        data=bytes(self.device.readAll())
        self.data.extend(data)
        values=self.samples(data)
        rms=math.sqrt(sum(x*x for x in values)/max(1,len(values)))
        self.level.emit(min(1,rms*6))
        if len(self.data)>12_000_000:
            self.timer.stop();QTimer.singleShot(0,self.stop)

    def stop(self,cancel=False):
        self.timer.stop()
        if not self.source:return
        self.read()
        source=self.source;self.source=None
        source.stop();source.deleteLater();self.level.emit(0)
        if cancel:self.data.clear();return
        values=self.samples(self.data);self.data.clear()
        channels=self.fmt.channelCount()
        mono=array.array('h',(max(-32768,min(32767,int(sum(values[i:i+channels])/channels*32767))) for i in range(0,len(values)-channels+1,channels)))
        if len(mono)<self.fmt.sampleRate()//4 or max((abs(x) for x in mono),default=0)<100:
            self.failed.emit('No clear speech recorded. Hold the ball or microphone button while speaking, then release.');return
        output=io.BytesIO()
        with wave.open(output,'wb') as wav:
            wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(self.fmt.sampleRate());wav.writeframes(mono.tobytes())
        self.finished.emit(output.getvalue())

def transcribe(config,audio):
    from openai import OpenAI
    model='whisper-large-v3-turbo' if 'api.groq.com' in config['base_url'] else 'whisper-1'
    with OpenAI(api_key=config['api_key'],base_url=config['base_url'],timeout=45,max_retries=0) as client:
        result=client.audio.transcriptions.create(model=model,file=('speech.wav',audio,'audio/wav'))
    text=result.text.strip()
    if not text:raise ValueError('The speech service returned no words. Try speaking closer to the microphone.')
    return text

def neural_speech(text,voice='en-US-AriaNeural',rate=0,cancel=None):
    import edge_tts
    async def generate():
        if cancel and cancel.is_set():return b''
        output=bytearray()
        async for chunk in edge_tts.Communicate(text[:12000],voice,rate=f'{round(rate*70):+d}%').stream():
            if cancel and cancel.is_set():return b''
            if chunk['type']=='audio':output.extend(chunk['data'])
        if not output:raise ValueError('The online voice service returned no audio. Try system voice or check your connection.')
        return bytes(output)
    return asyncio.run(asyncio.wait_for(generate(),timeout=60))
