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

ถาม: ถ้าต้องการลงทะเบียนน้อยกว่าเกณฑ์ต้องทำอย่างไร?
ตอบ: ยื่นคำร้องที่ว่าการ ลงนามอาจารย์ที่ปรึกษา

ถาม: ลงทะเบียนเพิ่มถอนทำได้ช่วงไหน?
ตอบ: ภายใน 3 สัปดาห์นับตั้งแต่เปิดเทอม

ถาม: ค่าลงทะเบียนสำหรับนักศึกษาปกติต้องชำระเท่าไร?
ตอบ: ชำระ 25,000 บาท ต่อภาคการศึกษา

ถาม: ค่าลงทะเบียนสำหรับนักศึกษาภาคฤดูร้อนต้องชำระเท่าไร?
ตอบ: ชำระ 5,000 บาท ต่อภาคการศึกษา

ถาม: นักศึกษาเรียนมาแล้ว 6 ปีแต่ยังลงทะเบียนไม่ครบ ยังสามารถลงทะเบียนได้ไหม?
ตอบ: ได้ครับ 6,000 บาท ต่อภาคการศึกษา

ถาม: ลงทะเบียนเกินกว่าจำนวนหน่วยกิตที่กำหนดสูงสุดได้ไหม?
ตอบ: ทำได้ภายใน 23 หน่วยกิต โดยต้องมีเกรดเฉลี่ยสะสมตั้งแต่ 3.00 ขึ้นไป Reg KMUTNB

ถาม: ถ้าเพิ่งเข้าศึกษาและต้องการลงทะเบียนก่อนกำหนดทำได้ไหม?
ตอบ: ตรวจสอบวันลงทะเบียน Reg KMUTNB ตามกำหนดการประจำปีการศึกษา

ถาม: ถ้าต้องการลงทะเบียนผ่านระบบออนไลน์ต้องทำอย่างไร?
ตอบ: เข้าไปที่ Reg KMUTNB ที่ reg.kmutnb.ac.th

ถาม: ถ้าลงทะเบียนช้าต้องเสียค่าปรับไหม?
ตอบ: ต้องเสียค่าปรับ 1-2 สัปดาห์

ถาม: ถ้าต้องการจบการศึกษาต้องลงทะเบียนวิชาอะไรบ้าง?
ตอบ: ต้องลงทะเบียนครบทุกวิชาตามหลักสูตรรวมถึงวิชา Senior Project หรือ Thesis ตามสาขาที่เรียน

ถาม: วิชาเลือกเสรีสามารถลงทะเบียนวิชาจากภาควิชาอื่นได้ไหม?
ตอบ: ได้ครับ แต่ต้องตรวจสอบว่าวิชานั้นนับเป็นวิชาเลือกเสรีในหลักสูตรของคุณหรือไม่

ถาม: ถ้าต้องการยกเลิกรายวิชาต้องทำอย่างไร?
ตอบ: ต้องยื่นคำร้องผ่านระบบ Reg KMUTNB ภายในระยะเวลาที่กำหนด

ถาม: ถ้าลงทะเบียนผิดพลาดต้องแก้ไขอย่างไร?
ตอบ: ติดต่อสำนักทะเบียนและประมวลผล Reg KMUTNB ตามระยะเวลาที่กำหนดไว้ในปฏิทินการศึกษา

ถาม: ภาควิชาอยู่ที่ไหน ที่อยู่คืออะไร?
ตอบ: ภาควิชาครุศาสตร์โยธา คณะครุศาสตร์อุตสาหกรรม มหาวิทยาลัยเทคโนโลยีพระจอมเกล้าพระนครเหนือ อาคาร 52 ชั้น 1 เลขที่ 1518 ถนนประชาราษฎร์ 1 แขวงวงศ์สว่าง เขตบางซื่อ กรุงเทพมหานคร 10800

ถาม: เบอร์โทรศัพท์ภาควิชาคืออะไร ติดต่อได้ที่ไหน?
ตอบ: โทรศัพท์ 02-555-2000 ต่อ 3247
"""

SYSTEM_PROMPT = f"""คุณคือผู้ช่วยตอบคำถามการลงทะเบียนเรียน ภาควิชาครุศาสตร์โยธา มจพ.

กฎเข้มงวด:
1. ตอบได้เฉพาะคำถามที่มีข้อมูลอยู่ในส่วน "ข้อมูล:" ด้านล่างเท่านั้น
2. ห้ามใช้ความรู้ของตัวเองตอบ ห้ามเดา ห้ามอนุมานข้อมูลใดๆ ทั้งสิ้น
3. หากไม่มีข้อมูลในระบบ ให้ตอบคำว่า NO_ANSWER เพียงอย่างเดียว ห้ามพิมพ์อะไรเพิ่มเติมเด็ดขาด
4. ตอบสั้นกระชับ ไม่เกิน 3 บรรทัด ภาษาไทย

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
        print(f"[GROQ OK] {reply_text[:80]}")
    except Exception as e:
        print(f"[GROQ ERROR] {type(e).__name__}: {e}")
        return

    if "NO_ANSWER" in reply_text.upper():
        print("[SKIP] No matching info, silent")
        return

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
