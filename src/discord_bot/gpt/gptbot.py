import base64
import os
import tempfile
import tomllib
import traceback
from logging import config, getLogger
from constants import Constants
from typing import Union
import discord
from discord import app_commands
from dotenv import load_dotenv


from openaiUtil import OpenAiUtil

project_root_abspath = os.path.dirname(os.path.abspath(__file__))
log_folder_abspath = os.path.join(project_root_abspath, "logs")
configpath = os.path.join(project_root_abspath, "pyproject.toml")
basename = os.path.basename(__file__).split(".")[0]
with open(configpath, "rb") as f:
    log_conf = tomllib.load(f).get("logging")
    log_conf["handlers"]["fileHandler"]["filename"] = os.path.join(log_folder_abspath, f"{basename}.log")

logger = getLogger(Constants.LOGGER_NAME)
config.dictConfig(log_conf)
dotenvpath = os.path.join(project_root_abspath, ".env")
load_dotenv(dotenvpath)

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN_GPT")
CHANNEL_ID = os.getenv("CHANNEL_ID_GPT")

openai_client = OpenAiUtil(
    key=os.getenv("OPENAI_API_KEY")
)


async def reply_openai_exception(retries: int, message: Union[discord.Message, discord.Interaction], emessage: str):
    """Handles exceptions that occur during OpenAI API calls and sends appropriate replies.

    Args:
        retries (int): The number of remaining retries.
        message (discord.Message or discord.Interaction): The message or interaction object representing the user's request.
        e (Exception): The exception that occurred during the API call.

    Returns:
        None: The function does not return any value.

    Raises:
        None: The function does not raise any exceptions.
    """
    if retries > 0:
        await message.reply(
            f"OpenAI APIでエラーが発生しました。リトライします（残回数{retries}）。\n{emessage}",
            mention_author=False,
        )
    else:
        await message.reply(
            f"OpenAI APIでエラーが発生しました。\n{emessage}", mention_author=False
        )


@client.event
async def on_ready():
    """on ready"""
    print(f"We have logged in as {client.user}")
    await tree.sync()


@tree.command(name="gpt-hflush", description="chat gptのチャット履歴を消去する")
async def gpt_delete(interaction: discord.Interaction):
    """delete chat history with ChatGPT.

    Args:
        interaction (discord.Interaction): interaction.
    """
    logger.info("command: gpt-hflush")
    openai_client.chat_log_flush()
    logger.info("Deleted chat logs.")
    response = "チャット履歴を削除しました。"
    await interaction.response.send_message(response)


@tree.command(name="gpt-switch", description="chat gptモデルを切り替える")
async def gpt_switch(interaction: discord.Interaction):
    """switching the ChatGPT model between gpt-3.5-turbo-1106 and gpt-4.

    Args:
        interaction (discord.Interaction): interaction.
    """
    logger.info("command: gpt-switch")
    model_engine_name = openai_client.model_switch()
    response = f"モデルエンジンを {model_engine_name} に変更しました。"
    logger.info("Change the model engine to " + model_engine_name)
    await interaction.response.send_message(response)


@tree.command(name="gpt-system", description="chat gptのキャラクター設定をする")
async def gpt_system(interaction: discord.Interaction, prompt: str):
    """set up ChatGPT character.

    Args:
        interaction (discord.Interaction): interaction.
        prompt (str): the setting of the ChatGPT character you want it to be.
    """
    logger.info("command: gpt-system")
    openai_client.role_change(prompt=prompt)
    logger.info("Set gpt character.")
    response = "role: systemを次のように設定しました:\n" + ">>> " + prompt
    await interaction.response.send_message(response)


@client.event
async def on_message(message):
    """
    Process the received message and generate a response.

    Args:
        message: The message object representing the received message.

    Returns:
        None

    Raises:
        Exception: If an error occurs while generating a response.

    """

    if message.author.bot:
        return
    if message.author == client.user:
        return
    if str(message.channel.id) == CHANNEL_ID:
        msg = await message.reply("生成中...", mention_author=False)

        prompt = message.content
        if not prompt:
            await msg.delete()
            await message.channel.send("質問内容がありません")
            return
        content = prompt
        if len(message.attachments) > 0 and openai_client.model_engine.value.isVision is True:
            for attachment in message.attachments:
                if attachment.content_type.startswith("image"):
                    # 画像のダウンロード
                    image_data = await attachment.read()
                    # 一時ファイルとして保存
                    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                        temp_file.write(image_data)
                    img_path = temp_file.name
                    # base64
                    with open(img_path, "rb") as image_file:
                        base64_image = base64.b64encode(image_file.read()).decode("utf-8")
                    content = [
                        {"type": "text", "text": f"{prompt}"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                                },
                        },
                    ]
        logger.info(f"user: {content}")

        retries = Constants.MAX_RETRY
        while retries > 0:
            try:
                response = openai_client.create_response(content=content)
                
                if  response.isError is True:
                    retries -= 1
                    await reply_openai_exception(retries, message,response.message[0])
                    continue
                
                await msg.delete()
                for response in response.message:
                    await message.reply(response, mention_author=False)
                break
            
            except discord.errors.HTTPException as e:
                logger.exception(e)
                await message.reply(
                    f"Discord APIでエラーが発生しました。\n{traceback.format_exception_only(e)}", mention_author=False
                )
                break
            except Exception as e:
                logger.exception(e)
                await message.reply(
                    f"エラーが発生しました。\n{traceback.format_exception_only(e)}", mention_author=False
                )
                break


logger.info("Start client.")
client.run(DISCORD_BOT_TOKEN)
