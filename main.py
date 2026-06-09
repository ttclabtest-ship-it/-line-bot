import os
from groq import Groq
from fastapi import FastAPI, Request, HTTPException
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)

app = FastAPI()

LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

print(f"[STARTUP] TOKEN={len(LINE_CHANNEL_ACCESS_TOKEN)} SECRET={len(LINE_CHANNEL_SECRET)} GROQ={len(GROQ_API_KEY)}")

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
groq_client = Groq(api_key=GROQ_API_KEY)

QA_DATA = """
ถาม: ลงทะเบียนได้กี่หน่วยกิต?
ตอบ: นักศึกษาปกติลงทะเบียนได้ไม่ต่ำกว่า 9 หน่วยกิต และไม่เกิน 22 หน่วยกิต

ถาม: ภาคฤดูร้อน ลงทะเบียนได้กี่หน่วยกิต?
ตอบ: ลงทะเบียนได้ไม่ต่ำกว่า 9 หน่วยกิต

ถาม: เริ่มลงทะเบียน เพิ่ม ถอน เปลี่ยนตอน ได้เมื่อไหร่?
ตอบ: ภายใน 3 สัปดาห์นับตั้งแต่วันเปิดเทอม

ถาม: ถอนวิชาเรียนได้ถึงเมื่อไหร่?
ตอบ: ภายใน 12 สัปดาห์หลังจากเปิดเรียน

ถาม: ค่าเทอมเสริมทักษะ ต้องจ่ายเท่าไหร่?
ตอบ: เหมาจ่าย 25,000 บาท ต่อภาคเรียน

ถาม: ค่าลงทะเบียนภาคฤดูร้อน ต้องจ่ายเท่าไหร่?
ตอบ: เหมาจ่าย 5,000 บาท ต่อภาคเรียน

ถาม: นักศึกษาชั้นปี 6 จ่ายค่าลงทะเบียนเท่าไหร่?
ตอบ: เหมาจ่าย 6,000 บาท ต่อภาคเรียน

ถาม: ลงทะเบียนเกินหน่วยกิตสูงสุดได้เท่าไหร่?
ตอบ: ไม่เกิน 23 หน่วยกิต โดยต้องยื่นคำร้องในระบบ Reg KMUTNB

ถาม: ไม่มีวิชาเรียนในภาคเรียนนี้ ต้องทำอย่างไร?
ตอบ: ต้องยื่นคำร้องในระบบ Reg KMUTNB ขอลาพักการเรียน

ถาม: ขอกลับเข้าศึกษาต่อ ต้องยื่นคำร้องเมื่อไหร่?
ตอบ: ยื่นก่อนวันลงทะเบียน 1-2 สัปดาห์

ถาม: ขอผ่อนผันค่าลงทะเบียนได้ถึงเมื่อไหร่?
ตอบ: วันสุดท้ายของการลงทะเบียนล่าช้าตามปฏิทินการศึกษา หรือก่อนสอบกลางภาค

ถาม: ตารางสอบชนกัน ต้องทำยังไง?
ตอบ: ยื่นคำร้องในระบบ Reg KMUTNB เพิ่มวิชาเรียนล่าช้า

ถาม: ไม่ได้ชำระเงินค่าลงทะเบียนตามกำหนด ต้องทำยังไง?
ตอบ: ยื่นคำร้องในระบบ Reg KMUTNB ผ่อนผันการลงทะเบียนและชำระเงินล่าช้ากรณีพิเศษ
"""

SYSTEM_PROMPT = f"""คุณคือผู้ช่วยสำหรับนักศึกษาภาควิชาครุศาสตร์โยธา มจพ.
ตอบคำถามเกี่ยวกับการลงทะเบียนเรียนโดยใช้ข้อมูลด้านล่างเท่านั้น
ตอบเป็นภาษาไทย กระชับ ชัดเจน และเป็นมิตร
หากคำถามไม่เกี่ยวข้องกับข้อมูลที่มี ให้แนะนำให้ติดต่อเจ้าหน้าที่โดยตรง

ข้อมูล:
{QA_DATA}"""


@app.post("/webhook")
async def webhook(request: Request):
        signature = request.headers.get("X-Line-Signature", "")
        body = await request.body()
        try:
                    handler.handle(body.decode("utf-8"), signature)
except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
except Exception as e:
        print(f"[HANDLER ERROR] {type(e).__name__}: {e}")
    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
        user_message = event.message.text
        print(f"[MSG] {user_message}")
        try:
                    response = groq_client.chat.completions.create(
                                    model="llama-3.1-8b-instant",
                                    messages=[
                                                        {"role": "system", "content": SYSTEM_PROMPT},
                                                        {"role": "user", "content": user_message}
                                    ]
                    )
                    reply_text = response.choices[0].message.content.strip()
                    print(f"[GROQ OK] {reply_text[:50]}")
except Exception as e:
        print(f"[GROQ ERROR] {type(e).__name__}: {e}")
        reply_text = "ขออภัยครับ เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง หรือติดต่อเจ้าหน้าที่โดยตรง"

    try:
                with ApiClient(configuration) as api_client:
                                line_bot_api = MessagingApi(api_client)
                                line_bot_api.reply_message(
                                    ReplyMessageRequest(
                                        reply_token=event.reply_token,
                                        messages=[TextMessage(text=reply_text)]
                                    )
                                )
                            print("[LINE] Reply sent OK")
except Exception as e:
        print(f"[LINE ERROR] {type(e).__name__}: {e}")


@app.get("/")
def root():
        return {"status": "LINE Chatbot is running with Groq!"}
