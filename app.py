from flask import Flask, request
import requests
import os
import google.generativeai as genai

app = Flask(__name__)

# Token này do bạn tự đặt, sẽ dùng để xác thực với Facebook sau này
VERIFY_TOKEN = "MAT_KHAU_KET_NOI_CUA_TOI"
# Token này lấy từ Facebook sau khi tạo App (sẽ hướng dẫn ở Bước 3)
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
# API Key của Gemini
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Cấu hình Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # Sử dụng model gemini-3.0-pro (hoặc model phù hợp có sẵn tại thời điểm đó)
    # Nếu không chạy được, hãy kiểm tra lại tên model chính xác
    try:
        model = genai.GenerativeModel('gemini-3.0-pro')
    except Exception as e:
        print(f"Error loading model: {e}")
        model = None
else:
    print("WARNING: GEMINI_API_KEY not found in environment variables.")
    model = None

@app.route('/', methods=['GET'])
def verify():
    # Facebook sẽ gọi vào đây để xác minh server của bạn còn sống và đúng là của bạn
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200
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
                        if model:   
                            try:
                                chat = model.start_chat(history=[])
                                response = chat.send_message(message_text)
                                response_text = response.text
                            except Exception as e:
                                response_text = f"Xin lỗi, tôi đang gặp sự cố khi liên hệ với Gemini: {str(e)}"
                                print(f"Gemini Error: {e}")
                        else:
                            response_text = "Chưa cấu hình Gemini API Key hoặc Model."

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
