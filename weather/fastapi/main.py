from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse
import openai
import json
import requests
import os

openai.api_key = "sk-proj-I1Ac8Iz_45fkC5XLQXZ1a1hvYJbZdRiQIhvGGMEKBbuNOS0w3Mzz7JWvI3iFmL4MO6nGisbSn2T3BlbkFJHewzBj_NV-"  # 본인 키로 교체

app = FastAPI()


def get_weather(location: str):
    api_key = "b23f85c70aec4f19ae422802252507"
    url = f"https://api.weatherapi.com/v1/current.json?key={api_key}&q={location}&aqi=no"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        # 주요 정보만 추출하여 반환
        return {
            "location": data["location"]["name"],
            "weather": data["current"]["condition"]["text"],
            "temp": data["current"]["temp_c"]
        }
    except Exception as e:
        return {"error": str(e)}

# 사용 예시
# print(get_weather("new york"))

@app.get("/")
def read_index():
    return FileResponse(os.path.join(os.path.dirname(__file__), "index.html"))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        req = json.loads(data)
        user_message = req.get("message", "")
        # 여기서 call_openai_with_functions는 일반 함수로 호출
        response = call_openai_with_functions(user_message)
        await websocket.send_text(json.dumps(response, ensure_ascii=False))

import openai
import json
import re

def translate_to_english(text: str) -> str:
    # 한글이 포함되어 있으면 번역, 아니면 그대로 반환
    if re.search('[가-힣]', text):
        # OpenAI API로 번역 요청
        completion = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a translation assistant."},
                {"role": "user", "content": f"Translate the following city name to English: '{text}'"}
            ]
        )
        return completion.choices[0].message.content.strip(' "\'')
    else:
        return text

def call_openai_with_functions(message):
    functions = [
        {
            "name": "get_weather",
            "description": "Get current weather information for a specific location. If location is in Korean, translate it to English before calling.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name. Korean is allowed, but will be translated to English before use."}
                },
                "required": ["location"]
            }
        }
    ]
    completion = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a weather assistant."},
            {"role": "user", "content": message}
        ],
        functions=functions,
        function_call="auto"
    )

    choice = completion.choices[0]
    if hasattr(choice.message, "function_call") and choice.finish_reason == "function_call":
        func_name = choice.message.function_call.name
        args = json.loads(choice.message.function_call.arguments)
        # 한글 입력시 영어로 변환
        location = args["location"]
        location_en = translate_to_english(location)
        if func_name == "get_weather":
            result = get_weather(location_en)
            return {"function": func_name, "result": result, "original_location": location, "translated_location": location_en}
    else:
        return {"response": choice.message.content}
