from cmath import log
from distutils.sysconfig import PREFIX
import discord
from dotenv import load_dotenv
import os
from discord.ext import commands
from datetime import datetime, timedelta
import threading
import random
import time
load_dotenv()

PREFIX = os.environ['PREFIX']
TOKEN = os.environ['TOKEN']

intents = discord.Intents.all()
intents.members = True

app = commands.Bot(command_prefix="/", intents=intents)
message_counts = {}
time_frames = {}
red_cards = {}

admin_id = 888839822184153089
semiadmin_id = 888817303188287519
semisemiadmin_id =1032632104367947866

# Time interval to keep data in memory (in seconds)
DATA_EXPIRATION_TIME = 3600

# 글자수 최대
threshold = 300

# 장문도배 경고문
WARNING_MESSAGES = ["장문 도배인가요?! 하지마세요!.",
                   "장문 도배가 감지되었습니다!",
                   "장문은 도배로 판단하겠습니다! 하지마세요!"
                   ]


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
    

    if message.content.startswith(app.command_prefix):
        # Process commands in a separate thread
        await app.loop.run_in_executor(None, app.process_commands, message)
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

@app.event
async def on_message(message):
    if message.content.startswith('아로나짱'):
        channel = message.channel
        await channel.send('MD Studio 관리 지원 Bot 아로나입니다! 제 역할이 궁금하다면 /arona 를 입력해주세요')

@app.command()
async def arona(ctx):
    await ctx.send("MD Studio 관리 지원 Bot 아로나입니다 제 역할은 입장 인원들을 반갑게 맞이하고\n인원들을 한국인과 일본인으로 분류하고\n 관리자님들을 도와 KR채널의 보안을 책임집니다.\n")

  try:
    app.run(TOKEN)
except discord.errors.LoginFailure as e:
    print("Improper token has been passed.")
