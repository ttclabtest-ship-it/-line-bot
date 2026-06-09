import os
import google.generativeai as genai
from fastapi import FastAPI, Request, HTTPException
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = FastAPI()

# ============================
# ตั้งค่า API Keys
# ============================
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# ============================
# ข้อมูล Q&A คำร้องนักศึกษา
# ภาควิชาครุศาสตร์โยธา มจพ.
# ============================
QA_DATA = """
ถาม: ลงทะเบียนได้กี่หน่วยกิต?
ตอบ: นักศึกษาปกติลงทะเบียนได้ไม่ต่ำกว่า 9 หน่วยกิต และไม่เกิน 22 หน่วยกิต

ถาม: ภาคฤดูร้อน (Summer) ลงทะเบียนได้กี่หน่วยกิต?
ตอบ: ลงทะเบียนได้ไม่ต่ำกว่า 9 หน่วยกิต

ถาม: เริ่มลงทะเบียน เพิ่ม ถอน เปลี่ยนตอน ได้เมื่อไหร่?
ตอบ: ภายใน 3 สัปดาห์นับตั้งแต่วันเปิดเทอม

ถาม: ถอนวิชาเรียนได้ถึงเมื่อไหร่?
ตอบ: ภายใน 12 สัปดาห์หลังจากเปิดเรียน (หลังทราบคะแนนสอบกลางภาค ภายใน 1 สัปดาห์)

ถาม: ค่าเทอมหรือค่าลงทะเบียนหลักสูตรเสริมทักษะ ต้องจ่ายเท่าไหร่?
ตอบ: เหมาจ่าย 25,000 บาท ต่อภาคเรียน (หลักสูตร 5 ปี จ่าย 10 เทอม)

ถาม: ค่าลงทะเบียนภาคฤดูร้อน (Summer) ต้องจ่ายเท่าไหร่?
ตอบ: เหมาจ่าย 5,000 บาท ต่อภาคเรียน

ถาม: นักศึกษาชั้นปี 6 ขึ้นไป จ่ายค่าลงทะเบียนเท่าไหร่?
ตอบ: เหมาจ่าย 6,000 บาท ต่อภาคเรียน

ถาม: ลงทะเบียนเกินหน่วยกิตสูงสุดได้เท่าไหร่?
ตอบ: ไม่เกิน 23 หน่วยกิต โดยต้องยื่นคำร้องในระบบ Reg KMUTNB ตามช่วงปฏิทินการศึกษา (กรณีสูง/ต่ำกว่าเกณฑ์ที่กำหนด ทั้งปกติและวิทยาทัณฑ์)

ถาม: เหลือลงทะเบียนเก็บวิชาเรียน 1 รายวิชา ต้องลงทะเบียนอย่างไร?
ตอบ: ยื่นคำร้องในระบบ Reg KMUTNB ลงทะเบียนตามช่วงปฏิทินการศึกษา กรณีสูง/ต่ำกว่าเกณฑ์ที่กำหนด (ปกติและวิทยาทัณฑ์)

ถาม: ไม่มีวิชาเรียนในภาคเรียนนี้ ต้องทำอย่างไร?
ตอบ: ต้องยื่นคำร้องในระบบ Reg KMUTNB ขอลาพักการเรียน โดยระบุเหตุผลว่า "เนื่องจากไม่มีรายวิชาที่ต้องลงทะเบียนในเทอมนี้"

ถาม: ขอกลับเข้าศึกษาต่อ ต้องยื่นคำร้องเมื่อไหร่?
ตอบ: ยื่นก่อนวันลงทะเบียนของเทอมที่นักศึกษาจะกลับมาเรียน 1-2 สัปดาห์ และเมื่อคำร้องได้รับการอนุมัติแล้วจึงจะลงทะเบียนได้

ถาม: ขอผ่อนผันค่าลงทะเบียนได้ถึงเมื่อไหร่?
ตอบ: วันสุดท้ายของการลงทะเบียนล่าช้าตามปฏิทินการศึกษา หรือก่อนสอบกลางภาค

ถาม: ตารางสอบชนกัน ลงทะเบียนไม่ได้ต้องทำยังไง?
ตอบ: ยื่นคำร้องในระบบ Reg KMUTNB เพิ่มวิชาเรียนล่าช้า (ก่อนสอบปลายภาค) กรณีวัน-เวลาสอบซ้ำซ้อน

ถาม: ไม่ได้ชำระเงินค่าลงทะเบียนตามกำหนด ต้องทำยังไง?
ตอบ: ยื่นคำร้องในระบบ Reg KMUTNB ผ่อนผันการลงทะเบียนและชำระเงินล่าช้ากรณีพิเศษ
"""

SYSTEM_PROMPT = f"""คุณคือผู้ช่วยสำหรับนักศึกษาภาควิชาครุศาสตร์โยธา มจพ. (KMUTNB)
ตอบคำถามเกี่ยวกับการลงทะเบียนเรียนโดยใช้ข้อมูลด้านล่างเท่านั้น
ตอบเป็นภาษาไทย กระชับ ชัดเจน และเป็นมิตร
หากคำถามไม่เกี่ยวข้องกับข้อมูลที่มี ให้แนะนำให้ติดต่อเจ้าหน้าที่โดยตรง

ข้อมูลที่มี:
{QA_DATA}
"""

# ============================
# Webhook Endpoint
# ============================
@app.post("/webhook")
async def webhook(request: Request):
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()
    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    return "OK"


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text
    try:
        response = model.generate_content(
            f"{SYSTEM_PROMPT}\n\nคำถามของนักศึกษา: {user_message}"
        )
        reply_text = response.text.strip()
    except Exception as e:
        print(f"[GEMINI ERROR] {type(e).__name__}: {e}")
        reply_text = "ขออภัยครับ เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง หรือติดต่อเจ้าหน้าที่โดยตรง"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )


@app.get("/")
def root():
    return {"status": "LINE Chatbot is running!"}
