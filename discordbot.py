from cmath import log
from distutils.sysconfig import PREFIX
import discord
from dotenv import load_dotenv
import os
load_dotenv()
from discord import Embed
import requests
from discord.ext import commands
from datetime import datetime, timedelta
import threading
import random
import time
from bs4 import BeautifulSoup
import asyncio
import pytz
import openai

PREFIX = os.environ['PREFIX']
TOKEN = os.environ['TOKEN']
OPENAI_API_KEY = os.environ['GPT']

app = commands.Bot(command_prefix='/',intents=discord.Intents.all())
translator = Translator()
message_counts = {}
time_frames = {}
red_cards = {}

admin_id = 888839822184153089
semiadmin_id = 888817303188287519
semisemiadmin_id =1032632104367947866

openai.api_key = OPENAI_API_KEY

# 이전 대화 내용을 담을 리스트
conversation_history = []

# Time interval to keep data in memory (in seconds)
DATA_EXPIRATION_TIME = 3600

# 글자수 최대
threshold = 300

# 장문도배 경고문
WARNING_MESSAGES = ["장문 도배인가요?! 하지마세요!.",
                   "장문 도배가 감지되었습니다!",
                   "장문은 도배로 판단하겠습니다! 하지마세요!"
                   ]

# 네이버 날씨 페이지에서 서울의 날씨 정보를 가져오는 함수
def get_seoul_weather():
    url = "https://search.naver.com/search.naver?query=서울 날씨"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    temperature = soup.select_one('div.temperature_text strong').text.strip().replace('현재 온도','')
    summary = soup.select_one('dl.summary_list')
    temp_feel = summary.select_one('dt.term:contains("체감") + dd.desc').text
    weather_desc = soup.select_one('span.weather.before_slash').text
    fine_dust = soup.select_one('a:contains("미세먼지") span.txt').text
    ultrafine_dust = soup.select_one('a:contains("초미세먼지") span.txt').text
    lowest_temp = soup.select_one('.lowest').text.strip().replace('최저기온', '')
    highest_temp = soup.select_one('.highest').text.strip().replace('최고기온', '')
    rain_info = soup.select_one('div.cell_weather')
    morning_rainfall = rain_info.select_one('span.weather_inner:nth-child(1) .rainfall').text
    afternoon_rainfall = rain_info.select_one('span.weather_inner:nth-child(2) .rainfall').text


    return {
        "temperature": temperature,
        "temp_feel": temp_feel,
        "weather_desc" : weather_desc,
        "fine_dust": fine_dust,
        "ultrafine_dust": ultrafine_dust,
        "lowest_temp": lowest_temp,
        "highest_temp": highest_temp,
        "morning_rainfall": morning_rainfall,
        "afternoon_rainfall": afternoon_rainfall

    }


@app.event
async def on_ready():
    print('Done')
    await app.change_presence(status=discord.Status.online, activity=None)
    channel = app.get_channel(1032650685180813312)
    message_id = 1087701328928706570
    message = None
    async for msg in channel.history(limit=None):
        if msg.id == message_id:
            message = msg
            break
    if message is None:
        message = await channel.send("🇰🇷:Korean\n🇯🇵:Japanese")
        await message.add_reaction("🇰🇷")
        await message.add_reaction("🇯🇵")

    while True:
        now = datetime.now(pytz.timezone("Asia/Seoul"))
        if now.hour == 7 and now.minute == 0:
            weather_info = get_seoul_weather()
            embed = Embed(title="서울 기준 오늘의 날씨 정보를 알려드립니다!", color=0x00AAFF)
            embed.add_field(name="현재기온", value=f"{weather_info['temperature']} (체감온도 {weather_info['temp_feel']})", inline=False)
            embed.add_field(name="최고기온", value=weather_info['highest_temp'], inline=False)
            embed.add_field(name="최저기온", value=weather_info['lowest_temp'], inline=False)
            embed.add_field(name="날씨", value=f"{weather_info['weather_desc']}(오전 강수 확률 {weather_info['morning_rainfall']} / 오후 강수 확률 {weather_info['afternoon_rainfall']})", inline=False)
            embed.add_field(name="미세먼지 농도", value=weather_info['fine_dust'], inline=False)
            embed.add_field(name="초미세먼지 농도", value=weather_info['ultrafine_dust'], inline=False)
            embed.set_footer(text="오늘도 화이팅입니다!")
            await app.get_channel(888816297784262739).send(embed=embed) # 채널ID에는 메시지를 전송할 디스코드 채널의 ID를 입력해주세요.
        await asyncio.sleep(60) #1분마다 체크

def is_spamming(author_id):
    now = datetime.now()
    time_frame = time_frames.get(author_id, now)
    message_count = message_counts.get(author_id, 0)
    
    # Set time frame for user to 5 seconds
    time_frames[author_id] = now + timedelta(seconds=2)
    
    # Reset message count and delete expired data if time frame has passed
    if now > time_frame:
        message_counts[author_id] = 0
        for key in list(time_frames.keys()):
            if now > time_frames[key] + timedelta(seconds=DATA_EXPIRATION_TIME):
                del time_frames[key]
                del message_counts[key]
                
        return False
    
    # Increase message count and check if spamming
    message_counts[author_id] = message_count + 1
    return message_count >= 5 # Change 5 to desired message count threshold

def decrease_red_cards():
    while True:
        for user_id in red_cards.copy():
            red_cards[user_id] -= 1
            if red_cards[user_id] == 0:
                del red_cards[user_id]
        time.sleep(60)

# 감소 쓰레드 시작
decrease_thread = threading.Thread(target=decrease_red_cards, daemon=True)
decrease_thread.start()

def add_red_card(user_id):
    red_cards[user_id] = red_cards.get(user_id, 0) + 1

@app.event
async def on_message(message):

    spam_messages = [
    f"{message.author.mention}님, 도배는 금물입니다!",
    f"{message.author.mention}님, 도배하지 마세요!",
    f"{message.author.mention}님, 도배는 안돼요.",
    f"{message.author.mention}님, 채팅이 너무 빨라요.",
    f"{message.author.mention}님, 도배라뇨! 관리자한테 다 이를거에요."
]
    message_length = len(message.content)

    if message.author == app.user:
        return
    
    # 메세지 길이가 최대 글자수 돌파하는지 체크
    if message_length > threshold:
        # 경고발사
        WARNING_MESSAGE = random.choice(WARNING_MESSAGES)
        await message.channel.send(WARNING_MESSAGE)

        add_red_card(message.author.id)
  
        if red_cards.get(message.author.id, 0) >= 2:
            guild = message.guild
            role_id = 1087892271703261316 # Replace with the role ID you want to give to the user
            role = guild.get_role(role_id)
            adrole = discord.utils.get(message.guild.roles, id=admin_id)
            sadrole = discord.utils.get(message.guild.roles, id=semiadmin_id)
            ssrole = discord.utils.get(message.guild.roles, id=semisemiadmin_id)
            member = guild.get_member(message.author.id)
            await member.add_roles(role)
            await message.channel.send(f"{message.author.mention}, {role.name} 역할을 부여했습니다! {adrole.mention},{sadrole.mention},{ssrole.mention} 관리자님 오실때까지 대기해주세요!.")
            

        return
    
    # Check if user is spamming
    elif is_spamming(message.author.id):
        spam_message = random.choice(spam_messages)
        await message.channel.send(spam_message)
        message_counts[message.author.id] = 0 # Reset message count for user

        add_red_card(message.author.id)

        if red_cards.get(message.author.id, 0) >= 3:
            guild = message.guild
            role_id = 1087892271703261316 # Replace with the role ID you want to give to the user
            role = guild.get_role(role_id)
            adrole = discord.utils.get(message.guild.roles, id=admin_id)
            sadrole = discord.utils.get(message.guild.roles, id=semiadmin_id)
            ssrole = discord.utils.get(message.guild.roles, id=semisemiadmin_id)
            member = guild.get_member(message.author.id)
            await member.add_roles(role)
            await message.channel.send(f"{message.author.mention}, {role.name} 역할을 부여했습니다! {adrole.mention},{sadrole.mention},{ssrole.mention} 관리자님이 오실때까지 대기해주세요!.")
          
        if message.author == app.user:
            return
        text = message.content
        if text.startswith('아로나 '):
            user_input = text[5:]

            # 이전 대화 내용을 포함하여 대화 진행
            conversation_history.append({"role": "user", "content": user_input})

            bot_response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "MD 스튜디오 디스코드 채널 서포트 AI 아로나입니다!."},
                    {"role": "user", "content": user_input}
                ] + conversation_history,  # 이전 대화 내용 추가
                temperature=0.5
            )

            # 대화 내용 업데이트
            conversation_history.append({"role": "assistant", "content": bot_response['choices'][0]['message']['content']})
        
            #print(bot_response)
            bot_text = '\n'.join([choice['message']['content'] for choice in bot_response['choices']])
            await message.channel.send(f"{bot_text}")
    return



@app.event
async def on_member_join(member):
    channel = app.get_channel(1087554522378948609)
    if member.bot:
        await member.add_roles(member.guild.get_role(888840043463053333), reason="Bot 역할 지급")
        await channel.send(f'{member.mention}님 아로나와 같은 Bot이네요 Bot 역할 지급하겠습니다!') # channel에 보내기
    else:
        await channel.send(f'{member.mention}님 한국인이신가요? 반갑습니다 rule 채널에서 공지 읽어주시고 role 채널에서 한국 선택해주세요!') # channel에 보내기

# 역할 부여 이모지와 해당 역할 ID를 딕셔너리 형태로 저장합니다.
# 딕셔너리의 키는 이모지 이름, 값은 해당 역할의 ID입니다.
ROLES = {
    "🇰🇷": 927148258885783582,  # 이모지와 해당 역할 ID를 수정해주세요.
    "🇯🇵": 888820786041880666,
}

# 이벤트 핸들러
@app.event
async def on_raw_reaction_add(payload):
    if payload.message_id == 1087701328928706570:  # 역할 부여를 받을 메시지 ID를 수정해주세요.
        guild = app.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        if member.bot:
            return

        emoji = payload.emoji.name
        if emoji in ROLES:
            role_id = ROLES[emoji]
            role = guild.get_role(role_id)
            await member.add_roles(role)

@app.event
async def on_raw_reaction_remove(payload):
    if payload.message_id == 1087701328928706570:  # 역할 부여를 받을 메시지 ID를 수정해주세요.
        guild = app.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        if member.bot:
            return

        emoji = payload.emoji.name
        if emoji in ROLES:
            role_id = ROLES[emoji]
            role = guild.get_role(role_id)
            await member.remove_roles(role)

try:
    app.run(TOKEN)
except discord.errors.LoginFailure as e:
    print("Improper token has been passed.")
