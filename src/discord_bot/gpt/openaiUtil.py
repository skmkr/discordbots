import openai
from dataclasses import dataclass
from enum import Enum
from logging import getLogger
from constants import Constants
import traceback
from typing import List ,Any
import math

@dataclass(frozen=True)
class ModelInfo:
    seq: int
    name: str
    isVision:bool
    
@dataclass(frozen=True)
class GptAPIResponseInfo:
    """
    openAPIのレスポンスを格納する構造体
    """
    isError: bool
    message:list[str]

class OpenAiUtil:
    
    class _ModelEngines(Enum):
        gpt_4_turbo = ModelInfo(1,'gpt-4-turbo',False)
        gpt_4_vision_preview = ModelInfo(2,'gpt-4-vision-preview',True)
        gpt_4_omni = ModelInfo(3,'gpt-4o',True)

    @property
    def model_engine(self):
        return self._model
    
    _total_token= 0
       
    def __init__(self,key) -> None:
        self._client = openai.OpenAI(api_key=key)
        self._chat_log = []
        character_role = self.read_system_role_file()
        self._system_set = [
            {
                "role": "system",
                "content": character_role
            }
        ]
        self._model =self._ModelEngines.gpt_4_omni
        self._logger = getLogger(Constants.LOGGER_NAME)
    
    def read_system_role_file(self)-> str:
        """
        Purpose: gptに指示する性格用の文字列を外部定義されたファイルから読み取る
        """
        
        file_path = 'systemrole.txt'
        file_content=''
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                file_content = file.read()
            
        except Exception as e:
            return ''
        
        return file_content        
        
    def create_response(self,content: Any | list[dict[str, str]]) -> GptAPIResponseInfo:
        """OpenAIのAPIを呼び、結果を返却する。
            長い文章は2000文字程度で分ける。(discordの一回の発言限界)
            タイムアウトエラー等の場合の判定用のフラグを含む

        Args:
            content (list[dict[str, str]]): _description_

        Returns:
            GptAPIResponseInfo: 結果の文章とともにリトライ判定用のエラーフラグも返す。
        """
        
        self._chat_log.append({"role": "user", "content": content})
        
        try:
            #現在のmodelが画像処理系以外の場合はキャラクター設定等を設定する
            #if  self.model_engine.value.isVision is False:
            #    input_chat_log = self._system_set + self._chat_log
            #else:
            #    input_chat_log= self._chat_log    
            input_chat_log = self._system_set + self._chat_log
            
            #openaiのレスポンス
            completions = self._client.chat.completions.create(
                model=self.model_engine.value.name, 
                messages=input_chat_log, 
                max_tokens=2000
            )
            raw_response = completions.choices[0].message.content
            response_list = self._split_string(raw_response)
            dict_message =completions.choices[0].message.to_dict()
            self._chat_log.append(dict_message)
            
            self._logger.info("assistant: " + dict_message["content"])
            
            plice = self._price_calc(completions.usage.prompt_tokens,completions.usage.completion_tokens)
            response_list.append(f"(USAGE: {plice} USD)")
            self._total_token += completions.usage.total_tokens
            
            if self._total_token > 4096 - 256:
                self._chat_log = self._chat_log[1:]
            
            self._logger.info(self._chat_log)
            return GptAPIResponseInfo(isError=False,message=response_list)
        
        except openai.APITimeoutError as e:
            self._logger.exception(e)
            emessage= traceback.format_exception_only(e)
            return GptAPIResponseInfo(isError=True,message=emessage)

        except openai.InternalServerError as e:
            self._logger.exception(e)
            self._chat_log = self._chat_log[1:]
            emessage= traceback.format_exception_only(e)
            return GptAPIResponseInfo(isError=True,message=emessage)
        
    def chat_log_flush(self) ->None:
        """chatlogの初期化
        """
        self._chat_log = []
        
    def role_change(self,prompt:str) -> None:
        """システムのキャラクタ付を変える

        Args:
            prompt (str): キャラ付けプロンプト
        """
        self._system_set = [
            {
                "role": "system",
                "content": prompt
            }
        ]
    
    def model_switch(self) -> str:
        """モデルエンジンを設定されている次のものに切り替える

        Returns:
            str: 設定されたモデル名
        """
        now_model_no = self.model_engine.value.seq
        
        for model in self._ModelEngines:
            if model.value.seq == now_model_no +1:
                self._model = model
                return model.value.name
        
        self._model = self._ModelEngines.gpt_4_turbo
        return self.model_engine.value.name
        
    
    def _split_string(self,text: str) -> List[str]:
        """
        Split a long string, possibly containing newlines and code blocks, into a
        list of strings each with maximum length 2000.

        The split is performed at the last newline before the 2000 character limit
        is reached, or at the 2000th character if the string is in a code block.
        If a split occurs within a code block, appropriate code block tags are
        added to maintain correct formatting.

        Empty strings are removed from the final list.

        Args:
            text (str): The string to split.

        Returns:
            List[str]: The list of split strings.
        """
        ret_list = []
        buffer = ""
        code_block_flag = False
        for line in text.split("\n"):
            if "```" in line:
                code_block_flag = not code_block_flag
            if len(buffer + line + "\n") <= 2000 or (len(buffer + line + "\n") > 2000 and code_block_flag):
                if code_block_flag and len(buffer + line + "```\n") > 2000:
                    ret_list.append(buffer + "```\n")
                    buffer = "```\n"
                buffer += line + "\n"
            else:
                ret_list.append(buffer)
                buffer = line + "\n"
        if buffer:
            ret_list.append(buffer)

        ret_list_clean = [s for s in ret_list if s != ""]
        return ret_list_clean


    def _round_to_digits(self,val: float, digits: int) -> float:
        """
        Rounds the given value to the specified number of digits.

        Args:
            val (float): The value to be rounded.
            digits (int): Number of digits to round to. Must be a positive integer.

        Returns:
            float: The value rounded to the specified number of digits.

        Examples:
            >>> round_to_digits(3.14159, 2)
            3.1
            >>> round_to_digits(0.00123456, 5)
            0.0012346
        """
        if val == 0:
            return 0
        else:
            return round(val, -int(math.floor(math.log10(abs(val))) + (1 - digits)))

    def _price_calc(self,input_token:int,output_token:int) -> float:
        """トークン数から料金を概算を計算する

        Args:
            input_token (int): インプットトークン数
            output_token (int): アウトプット数トークン数

        Returns:
            float: USD
        """
        match self.model_engine:
            case self._ModelEngines.gpt_4_vision_preview:
                return self._round_to_digits(
                    input_token * 0.01 / 1000 
                    + output_token * 0.03 / 1000, 
                    3
                )             
            case self._ModelEngines.gpt_4_turbo:
                return self._round_to_digits(input_token * 0.01 / 1000 + output_token * 0.03 / 1000, 3  )             
            case self._ModelEngines.gpt_4_omni:
                return self._round_to_digits(input_token * 0.005 / 1000 + output_token * 0.015 / 1000, 3  )             
            case _:
                return self._round_to_digits(
                    input_token * 0.01 / 1000
                    + output_token * 0.03 / 1000,
                    3
                )
        