from fastapi import FastAPI, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPCredentials

app = FastAPI()
security = HTTPBasic()

# Moderator credentials
MOD_USERNAME = "mod"
MOD_PASSWORD = "securepassword123"

def verify_credentials(credentials: HTTPCredentials = Depends(security)):
    if credentials.username != MOD_USERNAME or credentials.password != MOD_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard(username: str = Depends(verify_credentials)):
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Liquid Glass Moderator Dashboard</title>
        <style>
            * { box-sizing: border-box; }
            body {
                background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
                color: #f1f5f9;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                overflow: hidden;
            }
            .glass-card {
                background: rgba(255, 255, 255, 0.04);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                padding: 40px 30px;
                border-radius: 32px;
                border: 1px solid rgba(255, 255, 255, 0.08);
                width: 340px;
                text-align: center;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.1);
            }
            h2 {
                margin-bottom: 8px;
                font-size: 22px;
                font-weight: 600;
                letter-spacing: -0.5px;
                color: #ffffff;
            }
            p.subtitle {
                color: #94a3b8;
                font-size: 13px;
                margin-bottom: 25px;
            }
            input {
                width: 100%;
                padding: 14px 18px;
                margin: 8px 0;
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
                color: #fff;
                font-size: 15px;
                outline: none;
                transition: all 0.3s ease;
            }
            input::placeholder {
                color: #64748b;
            }
            input:focus {
                background: rgba(255, 255, 255, 0.08);
                border-color: rgba(56, 189, 248, 0.5);
                box-shadow: 0 0 15px rgba(56, 189, 248, 0.15);
            }
            button {
                width: 100%;
                padding: 14px;
                background: linear-gradient(135deg, #38bdf8 0%, #0ea5e9 100%);
                border: none;
                border-radius: 16px;
                color: #0f172a;
                font-weight: 700;
                font-size: 15px;
                cursor: pointer;
                margin-top: 15px;
                box-shadow: 0 10px 20px rgba(14, 165, 233, 0.3);
                transition: transform 0.2s ease, opacity 0.2s ease;
            }
            button:active {
                transform: scale(0.97);
            }
        </style>
    </head>
    <body>
        <div class="glass-card">
            <h2>Moderator Panel</h2>
            <p class="subtitle">Bot Control System</p>
            <form action="/add-coins" method="POST">
                <input type="text" name="user_id" placeholder="User ID / Username" required>
                <input type="number" name="amount" placeholder="Coins to Add" required>
                <button type="submit">Add Coins</button>
            </form>
        </div>
    </body>
    </html>
    """

@app.post("/add-coins", response_class=HTMLResponse)
async def add_coins(user_id: str = Form(...), amount: int = Form(...), username: str = Depends(verify_credentials)):
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Success</title>
        <style>
            body {{
                background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
                color: #f1f5f9;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }}
            .glass-card {{
                background: rgba(255, 255, 255, 0.04);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                padding: 40px 30px;
                border-radius: 32px;
                border: 1px solid rgba(255, 255, 255, 0.08);
                width: 320px;
                text-align: center;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
            }}
            h2 {{ color: #38bdf8; margin-top: 0; font-size: 24px; }}
            p {{ color: #cbd5e1; font-size: 15px; line-height: 1.5; }}
            a {{
                display: inline-block;
                margin-top: 20px;
                color: #38bdf8;
                text-decoration: none;
                font-weight: 600;
            }}
        </style>
    </head>
    <body>
        <div class="glass-card">
            <h2>Success!</h2>
            <p>Added <b>{amount}</b> coins to user <b>{user_id}</b>.</p>
            <a href="/">← Back to Dashboard</a>
        </div>
    </body>
    </html>
    """
  
