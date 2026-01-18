from flask import Flask, request
import requests
import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Token này do bạn tự đặt, sẽ dùng để xác thực với Facebook sau này
VERIFY_TOKEN = "MAT_KHAU_KET_NOI_CUA_TOI"
# Token này lấy từ Facebook sau khi tạo App (sẽ hướng dẫn ở Bước 3)
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
# API Key của Gemini
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Cấu hình Gemini Client
client = None
if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"Error configuring Gemini client: {e}")
else:
    print("WARNING: GEMINI_API_KEY not found in environment variables.")

@app.route('/', methods=['GET'])
def verify():
    # 1. Lấy tham số từ Facebook gửi sang
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    # 2. IN LOG RA MÀN HÌNH ĐỂ KIỂM TRA (Quan trọng)
    # Dùng file=sys.stdout để ép Render hiện log ngay lập tức
    print(f"=== CÓ YÊU CẦU GET MỚI ===", file=sys.stdout)
    print(f"Mode nhận được: {mode}", file=sys.stdout)
    print(f"Token nhận được: {token}", file=sys.stdout)
    print(f"Token mong đợi: {VERIFY_TOKEN}", file=sys.stdout)

    # 3. So sánh và trả lời
    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("=> XÁC THỰC THÀNH CÔNG! Đang trả về challenge.", file=sys.stdout)
        return challenge, 200
    
    if mode == "subscribe" and token != VERIFY_TOKEN:
        print("=> LỖI: Sai Token!", file=sys.stdout)
        return "Verification token mismatch", 403

    print("=> Không phải yêu cầu xác thực (Truy cập thường).", file=sys.stdout)
    return "Hello world", 200

@app.route('/', methods=['POST'])
def webhook():
    # Facebook gửi tin nhắn của người dùng vào đây
    data = request.get_json()
    
    if data['object'] == 'page':
        for entry in data['entry']:
            for messaging_event in entry['messaging']:
                if messaging_event.get('message'):
                    sender_id = messaging_event['sender']['id']
                    message_text = messaging_event['message'].get('text')
                    
                    if message_text:
                        # Logic xử lý tin nhắn với Gemini
                        response_text = ""
                        if client:
                            try:
                                # Sử dụng model model mới nhất user yêu cầu
                                response = client.models.generate_content(
                                    model='gemini-3-flash-preview',
                                    contents=message_text
                                )
                                response_text = response.text
                            except Exception as e:
                                response_text = f"Xin lỗi, tôi đang gặp sự cố khi liên hệ với Gemini: {str(e)}"
                                print(f"Gemini Error: {e}")
                        else:
                            response_text = "Chưa cấu hình Gemini API Key."

                        send_message(sender_id, response_text)
                        
    return "ok", 200

def send_message(recipient_id, text):
    # Hàm gửi tin nhắn lại cho người dùng
    params = {"access_token": PAGE_ACCESS_TOKEN}
    headers = {"Content-Type": "application/json"}
    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    r = requests.post("https://graph.facebook.com/v18.0/me/messages", params=params, headers=headers, json=data)
    if r.status_code != 200:
        print(f"Failed to send message: {r.status_code}, {r.text}")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
