from flask import Flask, render_template_string, request, redirect, url_for
import google.generativeai as genai
import os
import json
from datetime import datetime
import markdown

def markdown_to_html(md_text):
    """Конвертирует Markdown в HTML и убирает <p> обёртку"""
    html = markdown.markdown(md_text)
    if html.startswith("<p>") and html.endswith("</p>"):
        html = html[3:-4]
    return html




# Настройка Gemini
API_KEY = "AIzaSyDWTZ3xqGddRCCLvshZlnzKrXrqhR2Yebw"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

app = Flask(__name__)
chat_dir = "chats"
os.makedirs(chat_dir, exist_ok=True)

# Загружает список доступных чатов
def get_chat_list():
    chats = []
    for filename in sorted(os.listdir(chat_dir)):
        if filename.endswith(".json"):
            filepath = os.path.join(chat_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                title = data["title"]
                chats.append({"id": filename.replace(".json", ""), "title": title})
    return chats

# Загружает один чат
def load_chat(chat_id):
    filepath = os.path.join(chat_dir, f"{chat_id}.json")
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)["messages"]
    return []

# Сохраняет чат
def save_chat(chat_id, title, messages):
    filepath = os.path.join(chat_dir, f"{chat_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump({"title": title, "messages": messages}, f, ensure_ascii=False, indent=4)

# Генерация нового chat_id
def new_chat_id():
    files = os.listdir(chat_dir)
    ids = [int(f.split("_")[1].split(".")[0]) for f in files if f.startswith("chat_")]
    return f"chat_{max(ids) + 1 if ids else 1}"

# HTML шаблон
HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Чат с Gemini</title>
    <style>
        :root {
            --bg: #f4f6f8;
            --sidebar-bg: #1f2937;
            --sidebar-text: #f9fafb;
            --primary: #6366f1;
            --primary-dark: #4f46e5;
            --user-msg: #e0f7fa;
            --bot-msg: #f1f5f9;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: 'Segoe UI', sans-serif;
            background: var(--bg);
        }

        .sidebar {
            width: 280px;
            background: var(--sidebar-bg);
            color: var(--sidebar-text);
            padding: 20px;
            display: flex;
            flex-direction: column;
            height: 100vh;
            position: fixed;
            left: 0;
            top: 0;
            overflow-y: auto;
        }

        .sidebar h3 {
            margin-bottom: 20px;
            font-size: 1.2em;
        }

        .chat-list a {
            display: block;
            background: #374151;
            color: var(--sidebar-text);
            padding: 10px;
            margin-bottom: 8px;
            border-radius: 6px;
            text-decoration: none;
            transition: background 0.2s;
        }

        .chat-list a:hover {
            background: var(--primary);
        }

        .main {
            margin-left: 280px;
            padding: 20px;
            height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }

        .chat-box {
            width: 700px;
            height: 80vh;
            background: white;
            border-radius: 12px;
            padding: 20px;
            overflow-y: auto;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 15px;
            display: flex;
            flex-direction: column;
        }

        .chat-bubble {
            padding: 12px 16px;
            margin-bottom: 12px;
            border-radius: 12px;
            max-width: 75%;
            line-height: 1.6;
            word-wrap: break-word;
        }

        .user {
            background: var(--user-msg);
            align-self: flex-end;
            margin-left: auto;
        }

        .gemini {
            background: var(--bot-msg);
            align-self: flex-start;
            margin-right: auto;
        }

        form {
            display: flex;
            gap: 10px;
            width: 700px;
        }

        input[type="text"] {
            flex: 1;
            padding: 14px;
            font-size: 16px;
            border-radius: 10px;
            border: 1px solid #ccc;
            outline: none;
        }

        input[type="text"]:focus {
            border-color: var(--primary);
        }

        button {
            background: var(--primary);
            color: white;
            border: none;
            padding: 14px 20px;
            font-size: 16px;
            border-radius: 10px;
            cursor: pointer;
            transition: background 0.2s;
        }

        button:hover {
            background: var(--primary-dark);
        }

        .new-chat {
            margin-top: auto;
            display: block;
            background: #10b981;
            padding: 10px;
            text-align: center;
            color: white;
            border-radius: 6px;
            text-decoration: none;
            font-weight: bold;
            transition: background 0.2s;
        }

        .new-chat:hover {
            background: #059669;
        }

        .delete-link {
            color: #f87171;
            margin-left: 8px;
            text-decoration: none;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="sidebar">
        <h3>💬 Мои чаты</h3>
        <div class="chat-list">
            {% for chat in chats %}
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <a href="{{ url_for('chat', chat_id=chat.id) }}" style="flex: 1;">{{ chat.title }}</a>
                <a href="{{ url_for('delete_chat', chat_id=chat.id) }}"
                   onclick="return confirm('Удалить этот чат?')"
                   class="delete-link">🗑</a>
            </div>
            {% endfor %}
        </div>
        <a class="new-chat" href="{{ url_for('new_chat') }}">➕ Новый чат</a>
    </div>

    <div class="main">
        <div class="chat-box" id="chat-box">
            {% for msg in messages %}
                <div class="chat-bubble {{ msg.role }}">
                    <div>{{ msg.content | safe }}</div>
                </div>
            {% endfor %}
        </div>

        <form method="post" onsubmit="return handleSubmit();">
            <input type="text" name="message" id="messageInput" placeholder="Введите сообщение..." required autofocus>
            <button type="submit">Отправить</button>
        </form>
    </div>

    <script>
        // Автоскролл вниз
        const chatBox = document.getElementById("chat-box");
        chatBox.scrollTop = chatBox.scrollHeight;

        function handleSubmit() {
            const input = document.getElementById("messageInput");
            if (!input.value.trim()) return false;
            return true;
        }

        // Ctrl+Enter — новая строка, Enter — отправка
        document.getElementById("messageInput").addEventListener("keydown", function(event) {
            if (event.key === "Enter" && !event.ctrlKey) {
                event.preventDefault();
                this.form.submit();
            }
        });

        // Эффект "печатания" текста только у последнего сообщения от Gemini
const geminiBubbles = document.querySelectorAll('.gemini');
const lastGemini = geminiBubbles[geminiBubbles.length - 1];

if (lastGemini) {
    const textElement = lastGemini.querySelector('div');
    const fullText = textElement.innerHTML;
    let i = 0;
    textElement.innerHTML = "";  // Очистим для анимации

    const typeInterval = setInterval(() => {
        // Разбираем текст на символы
        textElement.innerHTML = fullText.slice(0, i);  // Добавляем текст по одному символу

        // Применяем эффект печатания с сохранением HTML
        if (i < fullText.length) {
            i++;
        } else {
            clearInterval(typeInterval);
        }
    }, 15);
}


    </script>
    
</body>
</html>
"""



# Главная — редирект на последний чат или новый
@app.route("/")
def home():
    chats = get_chat_list()
    if chats:
        return redirect(url_for('chat', chat_id=chats[-1]["id"]))
    else:
        return redirect(url_for("new_chat"))

# Новый чат
@app.route("/new")
def new_chat():
    chat_id = new_chat_id()
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    save_chat(chat_id, f"Чат от {now}", [])
    return redirect(url_for('chat', chat_id=chat_id))


# Работа с чатом
@app.route("/chat/<chat_id>", methods=["GET", "POST"])
def chat(chat_id):
    messages = load_chat(chat_id)
    if request.method == "POST":
        user_input = request.form["message"]
        messages.append({"role": "user", "content": user_input})
        
        # Создаём историю чата
        chat_obj = model.start_chat(
            history=[{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} for m in messages]
        )
        
        # Получаем ответ от модели
        response = chat_obj.send_message(user_input)
        
        # Преобразуем текст от модели в HTML
        response_text = markdown_to_html(response.text)
        
        # Сохраняем сообщение с форматированием
        messages.append({"role": "gemini", "content": response_text})
        
        save_chat(chat_id, f"Чат от {datetime.now().strftime('%d.%m.%Y %H:%M')}", messages)
    
    chats = get_chat_list()
    return render_template_string(HTML, messages=messages, chats=chats)


@app.route("/delete/<chat_id>")
def delete_chat(chat_id):
    filepath = os.path.join(chat_dir, f"{chat_id}.json")
    if os.path.exists(filepath):
        os.remove(filepath)
    return redirect(url_for("home"))
 

if __name__ == "__main__":
    app.run(debug=True) 