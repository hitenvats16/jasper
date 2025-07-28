from enum import Enum

class Language(str, Enum):
    Chinese = "Chinese"
    Chinese_Yue = "Chinese,Yue"
    English = "English"
    Arabic = "Arabic"
    Russian = "Russian"
    Spanish = "Spanish"
    French = "French"
    Portuguese = "Portuguese"
    German = "German"
    Turkish = "Turkish"
    Dutch = "Dutch"
    Ukrainian = "Ukrainian"
    Vietnamese = "Vietnamese"
    Indonesian = "Indonesian"
    Japanese = "Japanese"
    Italian = "Italian"
    Korean = "Korean"
    Thai = "Thai"
    Polish = "Polish"
    Romanian = "Romanian"
    Greek = "Greek"
    Czech = "Czech"
    Finnish = "Finnish"
    Hindi = "Hindi"
    auto = "auto"

class VoiceId(str, Enum):
    Wise_Woman = "Wise_Woman"
    Friendly_Person = "Friendly_Person"
    Inspirational_girl = "Inspirational_girl"
    Deep_Voice_Man = "Deep_Voice_Man"
    Calm_Woman = "Calm_Woman"
    Casual_Guy = "Casual_Guy"
    Lively_Girl = "Lively_Girl"
    Patient_Man = "Patient_Man"
    Young_Knight = "Young_Knight"
    Determined_Man = "Determined_Man"
    Lovely_Girl = "Lovely_Girl"
    Decent_Boy = "Decent_Boy"
    Imposing_Manner = "Imposing_Manner"
    Elegant_Man = "Elegant_Man"
    Abbess = "Abbess"
    Sweet_Girl_2 = "Sweet_Girl_2"
    Exuberant_Girl = "Exuberant_Girl"

class SampleRate(int, Enum):
    SR_8000 = 8000
    SR_16000 = 16000
    SR_22050 = 22050
    SR_24000 = 24000
    SR_32000 = 32000
    SR_44100 = 44100

class BitRate(int, Enum):
    BR_32000 = 32000
    BR_64000 = 64000
    BR_128000 = 128000
    BR_256000 = 256000

class VoiceEmotion(str, Enum):
    happy = "happy"
    sad = "sad"
    angry = "angry"
    fearful = "fearful"
    disgusted = "disgusted"
    surprised = "surprised"
    neutral = "neutral"

class AudioFormat(str, Enum):
    mp3 = "mp3"
    flac = "flac"
    pcm = "pcm"